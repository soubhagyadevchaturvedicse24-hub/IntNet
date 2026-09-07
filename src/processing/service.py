"""
Processing Domain Service for CRIMENET (Slice 4).
Handles asynchronous processing job orchestration, worker execution, forensic hash integrity verification,
EvidenceContract_v1 generation, BOLA/BFLA authorization, and audit trail logging.
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import time
import uuid
from typing import Optional, List, Dict, Any, Tuple

from src.auth.models import TokenPayload
from src.auth.service import AuthService
from src.authorization.policy_engine import PolicyEngine, AuthorizationRequest
from src.audit.service import AuditService
from src.cases.service import CaseService
from src.evidence.service import EvidenceService
from src.processing.models import ProcessingJob, JobStatus, ProcessingJobCreate
from src.processing.engine import ObservationEngine, RawDiskObservationEngine
from src.processing.repository import ProcessingRepository, SQLiteProcessingRepository, InMemoryProcessingRepository
from src.artifacts.service import ArtifactService
from src.observation.isolated_engine import IsolatedObservationEngine


class ProcessingService:
    def __init__(
        self,
        repository: Optional[ProcessingRepository] = None,
        engine: Optional[ObservationEngine] = None,
        e01_engine: Optional[ObservationEngine] = None,
        evidence_service: Optional[EvidenceService] = None,
        case_service: Optional[CaseService] = None,
        policy_engine: Optional[PolicyEngine] = None,
        audit_service: Optional[AuditService] = None,
        auth_service: Optional[AuthService] = None,
        artifact_service: Optional[ArtifactService] = None,
        output_base_dir: str = "DATA/processing_output"
    ):
        self.repository = repository or SQLiteProcessingRepository()
        self.engine = engine or RawDiskObservationEngine()
        self.e01_engine = e01_engine or IsolatedObservationEngine()
        self.evidence_service = evidence_service or EvidenceService()
        self.case_service = case_service or self.evidence_service.case_service
        self.policy_engine = policy_engine or self.evidence_service.policy_engine
        self.audit_service = audit_service or self.evidence_service.audit_service
        self.auth_service = auth_service or self.evidence_service.auth_service
        self.artifact_service = artifact_service or ArtifactService(
            policy_engine=self.policy_engine,
            audit_service=self.audit_service,
            auth_service=self.auth_service
        )
        self.output_base_dir = Path(output_base_dir).resolve()
        self.output_base_dir.mkdir(parents=True, exist_ok=True)
        self._executor = ThreadPoolExecutor(max_workers=4)

    def _verify_auth(
        self,
        actor: TokenPayload,
        action: str,
        resource_id: str,
        target_case_id: str,
        resource_owner_case_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        user = self.auth_service.get_user_by_id(actor.sub)
        user_authorized_cases = user.authorized_case_ids if user else []

        req = AuthorizationRequest(
            actor=actor,
            action=action,
            resource_type="processing_job",
            resource_id=resource_id,
            target_case_id=target_case_id,
            resource_owner_case_id=resource_owner_case_id,
            context=context
        )

        decision = self.policy_engine.evaluate(req, user_authorized_cases)

        # Audit event
        self.audit_service.record_event(
            actor_id=actor.sub,
            actor_role=actor.role.value,
            case_id=target_case_id,
            action=action,
            target_resource=f"processing_job:{resource_id}",
            decision="ALLOW" if decision.allowed else "DENY",
            metadata={"reason": decision.reason}
        )

        if not decision.allowed:
            raise PermissionError(decision.reason)

    def create_processing_job(
        self,
        actor: TokenPayload,
        case_id: str,
        evidence_id: str,
        create_req: Optional[ProcessingJobCreate] = None
    ) -> ProcessingJob:
        # 1. Fetch & verify target evidence
        evidence = self.evidence_service.get_evidence(actor, case_id, evidence_id)
        if not evidence:
            raise KeyError(f"Evidence '{evidence_id}' not found under case '{case_id}'.")

        # 2. Check case status (Closed case processing protection)
        case = self.case_service.get_case(actor, case_id)
        if not case:
            raise KeyError(f"Case '{case_id}' not found.")

        if case.status.value == "CLOSED":
            raise PermissionError("CLOSED CASE DENY: Processing jobs cannot be launched on closed cases.")

        job_id = f"JOB-{time.strftime('%Y')}-{uuid.uuid4().hex[:6].upper()}"

        # 3. Authorization check
        self._verify_auth(
            actor=actor,
            action="START_PROCESSING",
            resource_id=job_id,
            target_case_id=case_id,
            resource_owner_case_id=evidence.case_id
        )

        output_dir = self.output_base_dir / case_id / job_id

        # 4. Compute pre-processing SHA-256 hash directly from storage
        pre_sha256 = self.evidence_service.storage.calculate_stored_sha256(evidence.storage_reference)
        if pre_sha256 != evidence.sha256:
            raise ValueError(f"CRITICAL FORENSIC ALERT: Pre-processing integrity mismatch for evidence '{evidence_id}'!")

        # Detect container image format
        ext = Path(evidence.original_filename).suffix.lower()
        image_format = "E01" if ext in ['.e01', '.e02'] else "RAW"
        selected_engine = self.e01_engine if image_format == "E01" else self.engine

        job = ProcessingJob(
            job_id=job_id,
            case_id=case_id,
            evidence_id=evidence_id,
            status=JobStatus.QUEUED,
            engine_name=selected_engine.get_engine_name(),
            engine_version=selected_engine.get_engine_version(),
            image_format=image_format,
            created_at=time.time(),
            requested_by=actor.sub,
            output_directory=str(output_dir),
            pre_processing_sha256=pre_sha256
        )

        self.repository.save(job)

        # Audit Event
        self.audit_service.record_event(
            actor_id=actor.sub,
            actor_role=actor.role.value,
            case_id=case_id,
            action="PROCESSING_REQUESTED",
            target_resource=f"processing_job:{job_id}",
            decision="ALLOW"
        )

        # Submit background worker execution
        self._executor.submit(self._run_job_worker, job.job_id, evidence.storage_reference)

        return job

    def _run_job_worker(self, job_id: str, storage_reference: str):
        job = self.repository.get_by_id(job_id)
        if not job:
            return

        job.status = JobStatus.RUNNING
        job.started_at = time.time()
        self.repository.save(job)

        self.audit_service.record_event(
            actor_id=job.requested_by,
            actor_role="SYSTEM_WORKER",
            case_id=job.case_id,
            action="PROCESSING_STARTED",
            target_resource=f"processing_job:{job_id}",
            decision="ALLOW"
        )

        try:
            stored_file_path = self.evidence_service.storage.base_dir / storage_reference
            output_dir_path = Path(job.output_directory)

            # Execute appropriate observation engine based on image format
            selected_engine = self.e01_engine if job.image_format == "E01" else self.engine
            contract_v1, observed_fs = selected_engine.process(
                image_path=stored_file_path,
                output_dir=output_dir_path,
                case_id=job.case_id,
                evidence_id=job.evidence_id,
                job_id=job.job_id
            )

            # Slice 6: Ingest observed artifacts into Artifact Domain
            try:
                self.artifact_service.ingest_contract_artifacts(contract_v1, job)
            except Exception as e:
                # Log non-fatal error during artifact ingestion
                print(f"Artifact ingestion warning for job {job.job_id}: {e}")

            # Forensic Integrity Post-Verification (Assert original bytes unchanged)
            post_sha256 = self.evidence_service.storage.calculate_stored_sha256(storage_reference)
            job.post_processing_sha256 = post_sha256

            if post_sha256 != job.pre_processing_sha256:
                job.status = JobStatus.FAILED
                job.error_message = f"CRITICAL FORENSIC CORRUPTION: Original evidence bytes modified during processing!"
                self.repository.save(job)
                self.audit_service.record_event(
                    actor_id=job.requested_by,
                    actor_role="SYSTEM_WORKER",
                    case_id=job.case_id,
                    action="PROCESSING_FAILED",
                    target_resource=f"processing_job:{job_id}",
                    decision="DENY",
                    metadata={"reason": job.error_message}
                )
                return

            job.observed_filesystem = observed_fs
            job.evidence_contract_ref = f"EV-CONTRACT-{job.job_id}"
            job.status = JobStatus.COMPLETED
            job.completed_at = time.time()
            self.repository.save(job)

            self.audit_service.record_event(
                actor_id=job.requested_by,
                actor_role="SYSTEM_WORKER",
                case_id=job.case_id,
                action="PROCESSING_COMPLETED",
                target_resource=f"processing_job:{job_id}",
                decision="ALLOW"
            )

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = time.time()
            self.repository.save(job)
            self.audit_service.record_event(
                actor_id=job.requested_by,
                actor_role="SYSTEM_WORKER",
                case_id=job.case_id,
                action="PROCESSING_FAILED",
                target_resource=f"processing_job:{job_id}",
                decision="DENY",
                metadata={"reason": str(e)}
            )

    def get_job(self, actor: TokenPayload, job_id: str) -> Optional[ProcessingJob]:
        job = self.repository.get_by_id(job_id)
        if not job:
            return None

        self._verify_auth(
            actor=actor,
            action="VIEW_PROCESSING_JOB",
            resource_id=job_id,
            target_case_id=job.case_id
        )
        return job

    def list_evidence_jobs(self, actor: TokenPayload, case_id: str, evidence_id: str) -> List[ProcessingJob]:
        evidence = self.evidence_service.get_evidence(actor, case_id, evidence_id)
        if not evidence:
            return []
        return self.repository.list_by_evidence(evidence_id)

    def get_evidence_contract(self, actor: TokenPayload, job_id: str) -> Optional[Dict[str, Any]]:
        job = self.get_job(actor, job_id)
        if not job or job.status != JobStatus.COMPLETED:
            return None

        contract_file = Path(job.output_directory) / f"evidence_contract_{job.job_id}.json"
        if not contract_file.exists():
            return None

        with open(contract_file, 'r', encoding='utf-8') as f:
            return json.load(f)
