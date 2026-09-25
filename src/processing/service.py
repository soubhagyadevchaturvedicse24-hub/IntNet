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
        entity_graph_service: Optional[Any] = None,
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
        self.entity_graph_service = entity_graph_service
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

            # Automatic Comprehensive Forensic Graph & Entity Resolution Post-Processing
            try:
                # 1. Construct authorized actor payload for job.case_id
                user = self.auth_service.get_user_by_id(job.requested_by)
                if user:
                    if job.case_id not in user.authorized_case_ids:
                        user.authorized_case_ids.append(job.case_id)
                    actor_payload = TokenPayload(
                        sub=user.user_id,
                        username=user.username,
                        role=user.role,
                        judicial_context=user.judicial_context,
                        exp=int(time.time()) + 7200,
                        jti=uuid.uuid4().hex
                    )
                else:
                    from src.auth.models import User, UserRole
                    self.auth_service._user_db[job.requested_by] = User(
                        user_id=job.requested_by,
                        username="system_worker",
                        password_hash="mock",
                        role=UserRole.INVESTIGATION_OFFICER,
                        authorized_case_ids=[job.case_id]
                    )
                    actor_payload = TokenPayload(
                        sub=job.requested_by,
                        username="system_worker",
                        role=UserRole.INVESTIGATION_OFFICER,
                        judicial_context=None,
                        exp=int(time.time()) + 7200,
                        jti=uuid.uuid4().hex
                    )

                from src.parsers.repository import SQLiteParsedArtifactRepository
                parsed_repo = SQLiteParsedArtifactRepository()

                eg_svc = getattr(self, "entity_graph_service", None)
                if eg_svc is None:
                    from src.entity_resolution.service import EntityGraphService
                    eg_svc = EntityGraphService(
                        processing_service=self,
                        evidence_service=self.evidence_service,
                        case_service=self.case_service,
                        policy_engine=self.policy_engine,
                        audit_service=self.audit_service,
                        auth_service=self.auth_service,
                        parsed_repo=parsed_repo
                    )
                    self.entity_graph_service = eg_svc

                # 2. Ingest Evidence Contract entities (phones, emails, regex signals)
                try:
                    eg_svc.ingest_evidence_contract(
                        actor=actor_payload,
                        case_id=job.case_id,
                        job_id=job.job_id
                    )
                except Exception as e:
                    print(f"Contract entity ingestion notice: {e}")

                # 3. Priority Deep Parsing & Evidence-Derived Observation Extraction
                from src.parsers.registry import ParserRegistry
                from src.parsers.repository import SQLiteParsedArtifactRepository
                from src.parsers.models import ParsingStatus, ParserType

                parser_registry = ParserRegistry()
                parsed_repo = SQLiteParsedArtifactRepository()

                art_dir = output_dir_path / "extracted_artifacts"
                extracted_file_map = {}
                if art_dir.exists() and art_dir.is_dir():
                    for f in art_dir.iterdir():
                        if f.is_file():
                            extracted_file_map[f.name.lower()] = f

                # Build candidate targets from contract observed artifacts
                observed_artifacts = contract_v1.get("observed_artifacts", [])

                # Priority sorting:
                # 1. Databases (autopsy.db, *.sqlite, *.db)
                # 2. Images (*.jpg, *.jpeg, *.png, *.tiff, *.webp) - for real EXIF GPS
                # 3. Documents (*.pdf)
                def _artifact_priority(a):
                    aname = (a.get("artifact_name") or "").lower()
                    atype = (a.get("artifact_type") or "").upper()
                    if "autopsy.db" in aname or atype == "DATABASE" or aname.endswith((".db", ".sqlite", ".sqlite3")):
                        return 0
                    if atype == "IMAGE" or aname.endswith((".jpg", ".jpeg", ".png", ".tiff", ".webp")):
                        return 1
                    if atype == "DOCUMENT" or aname.endswith(".pdf"):
                        return 2
                    return 3

                sorted_artifacts = sorted(observed_artifacts, key=_artifact_priority)

                import os
                max_deep_parse = int(os.getenv("CRIMENET_MAX_DEEP_PARSE_FILES", "150"))
                max_file_size = 50 * 1024 * 1024  # 50 MB safety limit

                parse_stats = {"processed": 0, "skipped": 0, "skip_reasons": {}}

                for idx, a in enumerate(sorted_artifacts):
                    aname = a.get("artifact_name") or ""
                    art_id = a.get("artifact_id", f"ART-{job.case_id}-{job.job_id}-{idx+1:03d}")
                    rel_path = a.get("content_path", "")

                    # Locate candidate file on disk
                    cand_path = None
                    if rel_path:
                        p1 = output_dir_path / "extracted_artifacts" / Path(rel_path).name
                        if p1.exists() and p1.is_file():
                            cand_path = p1
                        else:
                            p2 = (self.output_base_dir / rel_path).resolve()
                            if p2.exists() and p2.is_file():
                                cand_path = p2
                    if not cand_path:
                        cand_path = extracted_file_map.get(Path(aname).name.lower())

                    if not cand_path or not cand_path.exists():
                        parse_stats["skipped"] += 1
                        parse_stats["skip_reasons"]["FILE_NOT_ON_DISK"] = parse_stats["skip_reasons"].get("FILE_NOT_ON_DISK", 0) + 1
                        continue

                    # Check bounded budget
                    if parse_stats["processed"] >= max_deep_parse:
                        parse_stats["skipped"] += 1
                        parse_stats["skip_reasons"]["BUDGET_EXCEEDED"] = parse_stats["skip_reasons"].get("BUDGET_EXCEEDED", 0) + 1
                        continue

                    # Check file size limit
                    f_size = cand_path.stat().st_size
                    if f_size > max_file_size:
                        parse_stats["skipped"] += 1
                        parse_stats["skip_reasons"]["EXCEEDS_SIZE_LIMIT"] = parse_stats["skip_reasons"].get("EXCEEDS_SIZE_LIMIT", 0) + 1
                        continue

                    # Magic-byte parser detection
                    parser = parser_registry.get_parser_for_file(cand_path)
                    if parser.get_parser_type() == ParserType.UNSUPPORTED:
                        parse_stats["skipped"] += 1
                        parse_stats["skip_reasons"]["UNSUPPORTED_FORMAT"] = parse_stats["skip_reasons"].get("UNSUPPORTED_FORMAT", 0) + 1
                        continue

                    # Strict 5-part provenance metadata
                    art_meta = {
                        "artifact_id": art_id,
                        "case_id": job.case_id,
                        "evidence_id": job.evidence_id,
                        "job_id": job.job_id,
                        "filename": cand_path.name,
                        "sha256": a.get("sha256") or "",
                        "category": a.get("artifact_type", "OTHER"),
                    }

                    try:
                        parsed_artifact = parser.parse(file_path=cand_path, artifact_metadata=art_meta)
                        parsed_repo.save(parsed_artifact)
                        parse_stats["processed"] += 1
                    except Exception as pe:
                        parse_stats["skipped"] += 1
                        parse_stats["skip_reasons"]["PARSER_ERROR"] = parse_stats["skip_reasons"].get("PARSER_ERROR", 0) + 1
                        print(f"Deep parsing error for {cand_path.name}: {pe}")

                print(f"[DEEP PARSE] Completed for {job.job_id}: {parse_stats['processed']} processed, {parse_stats['skipped']} skipped. Reasons: {parse_stats['skip_reasons']}")

                # 4. Ingest evidence contract entities (phones, emails, regex signals from raw container)
                try:
                    eg_svc.ingest_evidence_contract(
                        actor=actor_payload,
                        case_id=job.case_id,
                        job_id=job.job_id
                    )
                except Exception as e:
                    print(f"Contract entity ingestion notice: {e}")

                # 5. Ingest deep parsed observations into Kùzu Graph DB
                try:
                    eg_svc.ingest_parsed_observations(
                        actor=actor_payload,
                        case_id=job.case_id,
                        job_id=job.job_id
                    )
                except Exception as e:
                    print(f"Observation graph ingestion notice: {e}")

            except Exception as e:
                print(f"Graph post-processing warning for job {job.job_id}: {e}")

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
