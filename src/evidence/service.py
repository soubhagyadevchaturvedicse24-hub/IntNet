"""
Evidence Domain Service for CRIMENET (Slice 3).
Handles evidence intake, file byte preservation, SHA-256 verification, BOLA/BFLA authorization, and audit logging.
"""

import time
import uuid
from typing import Optional, List, Dict, Any

from src.auth.models import TokenPayload
from src.auth.service import AuthService
from src.authorization.policy_engine import PolicyEngine, AuthorizationRequest
from src.audit.service import AuditService
from src.cases.service import CaseService
from src.evidence.models import (
    Evidence, EvidenceType, PreservationStatus, IntegrityStatus,
    EvidenceCreate, EvidenceVerifyResponse
)
from src.evidence.storage import EvidenceStorage, LocalFileStorage
from src.evidence.repository import EvidenceRepository, SQLiteEvidenceRepository, InMemoryEvidenceRepository


class EvidenceService:
    def __init__(
        self,
        repository: Optional[EvidenceRepository] = None,
        storage: Optional[EvidenceStorage] = None,
        case_service: Optional[CaseService] = None,
        policy_engine: Optional[PolicyEngine] = None,
        audit_service: Optional[AuditService] = None,
        auth_service: Optional[AuthService] = None
    ):
        self.repository = repository or SQLiteEvidenceRepository()
        self.storage = storage or LocalFileStorage()
        self.case_service = case_service or CaseService()
        self.policy_engine = policy_engine or self.case_service.policy_engine
        self.audit_service = audit_service or self.case_service.audit_service
        self.auth_service = auth_service or self.case_service.auth_service

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
            resource_type="evidence",
            resource_id=resource_id,
            target_case_id=target_case_id,
            resource_owner_case_id=resource_owner_case_id,
            context=context
        )

        decision = self.policy_engine.evaluate(req, user_authorized_cases)

        # Record Audit Event
        self.audit_service.record_event(
            actor_id=actor.sub,
            actor_role=actor.role.value,
            case_id=target_case_id,
            action=action,
            target_resource=f"evidence:{resource_id}",
            decision="ALLOW" if decision.allowed else "DENY",
            metadata={"reason": decision.reason}
        )

        if not decision.allowed:
            raise PermissionError(decision.reason)

    def register_evidence(
        self,
        actor: TokenPayload,
        case_id: str,
        create_req: EvidenceCreate,
        raw_filename: str,
        content: bytes
    ) -> Evidence:
        if not content:
            raise ValueError("Empty evidence file provided. Cannot register 0-byte evidence.")

        # Ensure target case exists
        case = self.case_service.repository.get_by_id(case_id)
        if not case:
            raise KeyError(f"Case '{case_id}' not found.")

        # Verify case status
        ctx = {"target_case_status": case.status.value}

        temp_ev_id = f"EV-{time.strftime('%Y')}-{uuid.uuid4().hex[:12].upper()}"

        # Verify authorization
        self._verify_auth(
            actor=actor,
            action="REGISTER_EVIDENCE",
            resource_id=temp_ev_id,
            target_case_id=case_id,
            context=ctx
        )

        # Preserve raw bytes to disk
        storage_ref, sha256_hash, md5_hash, size_bytes = self.storage.save_bytes(
            case_id=case_id,
            evidence_id=temp_ev_id,
            raw_filename=raw_filename,
            content=content
        )

        contract_ref = f"EV-CONTRACT-{time.strftime('%Y')}-{uuid.uuid4().hex[:12].upper()}"
        now = time.time()

        evidence = Evidence(
            evidence_id=temp_ev_id,
            case_id=case_id,
            evidence_name=create_req.evidence_name,
            evidence_type=create_req.evidence_type,
            original_filename=raw_filename,
            original_size_bytes=size_bytes,
            storage_reference=storage_ref,
            sha256=sha256_hash,
            md5=md5_hash,
            registered_at=now,
            registered_by=actor.sub,
            source_description=create_req.source_description,
            preservation_status=PreservationStatus.PRESERVED,
            integrity_status=IntegrityStatus.INTACT,
            evidence_contract_ref=contract_ref
        )

        # Register evidence resource mapping in PDP engine
        self.policy_engine.register_resource_case(temp_ev_id, case_id)

        self.repository.save(evidence)
        return evidence

    def register_local_evidence(
        self,
        actor: TokenPayload,
        case_id: str,
        create_req: EvidenceCreate,
        local_path: str
    ) -> Evidence:
        # Ensure target case exists
        case = self.case_service.repository.get_by_id(case_id)
        if not case:
            raise KeyError(f"Case '{case_id}' not found.")

        # Verify case status
        ctx = {"target_case_status": case.status.value}
        temp_ev_id = f"EV-{time.strftime('%Y')}-{uuid.uuid4().hex[:12].upper()}"

        # Verify authorization
        self._verify_auth(
            actor=actor,
            action="REGISTER_EVIDENCE",
            resource_id=temp_ev_id,
            target_case_id=case_id,
            context=ctx
        )

        # Link local forensic image via storage engine
        storage_ref, sha256_hash, md5_hash, size_bytes = self.storage.link_local_evidence(
            case_id=case_id,
            evidence_id=temp_ev_id,
            source_path_str=local_path
        )

        from pathlib import Path
        raw_filename = Path(local_path).name
        contract_ref = f"EV-CONTRACT-{time.strftime('%Y')}-{uuid.uuid4().hex[:12].upper()}"
        now = time.time()

        evidence = Evidence(
            evidence_id=temp_ev_id,
            case_id=case_id,
            evidence_name=create_req.evidence_name,
            evidence_type=create_req.evidence_type,
            original_filename=raw_filename,
            original_size_bytes=size_bytes,
            storage_reference=storage_ref,
            sha256=sha256_hash,
            md5=md5_hash,
            registered_at=now,
            registered_by=actor.sub,
            source_description=create_req.source_description,
            preservation_status=PreservationStatus.PRESERVED,
            integrity_status=IntegrityStatus.INTACT,
            evidence_contract_ref=contract_ref
        )

        # Register evidence resource mapping in PDP engine
        self.policy_engine.register_resource_case(temp_ev_id, case_id)
        self.repository.save(evidence)
        return evidence

    def register_staged_evidence(
        self,
        actor: TokenPayload,
        case_id: str,
        create_req: EvidenceCreate,
        staging_id: str
    ) -> Evidence:
        """
        Promotes quarantined staged forensic evidence into official case evidence storage.
        Preserves original bytes, registers cryptographic hashes, enforces BOLA/BFLA,
        and generates an Evidence entity.
        """
        case = self.case_service.repository.get_by_id(case_id)
        if not case:
            raise KeyError(f"Case '{case_id}' not found.")

        ctx = {"target_case_status": case.status.value}
        temp_ev_id = f"EV-{time.strftime('%Y')}-{uuid.uuid4().hex[:12].upper()}"

        self._verify_auth(
            actor=actor,
            action="REGISTER_EVIDENCE",
            resource_id=temp_ev_id,
            target_case_id=case_id,
            context=ctx
        )

        storage_ref, sha256_hash, md5_hash, size_bytes = self.storage.promote_staged_evidence(
            case_id=case_id,
            evidence_id=temp_ev_id,
            staging_id=staging_id
        )

        session_meta = self.storage.get_staging_session(staging_id) or {}
        raw_filename = session_meta.get("primary_file") or f"{temp_ev_id}.E01"
        contract_ref = f"EV-CONTRACT-{time.strftime('%Y')}-{uuid.uuid4().hex[:4].upper()}"
        now = time.time()

        evidence = Evidence(
            evidence_id=temp_ev_id,
            case_id=case_id,
            evidence_name=create_req.evidence_name,
            evidence_type=create_req.evidence_type,
            original_filename=raw_filename,
            original_size_bytes=size_bytes,
            storage_reference=storage_ref,
            sha256=sha256_hash,
            md5=md5_hash,
            registered_at=now,
            registered_by=actor.sub,
            source_description=create_req.source_description,
            preservation_status=PreservationStatus.PRESERVED,
            integrity_status=IntegrityStatus.INTACT,
            evidence_contract_ref=contract_ref
        )

        self.policy_engine.register_resource_case(temp_ev_id, case_id)
        self.repository.save(evidence)
        return evidence

    def get_evidence(self, actor: TokenPayload, case_id: str, evidence_id: str) -> Optional[Evidence]:
        evidence = self.repository.get_by_id(evidence_id)
        if not evidence:
            # Check if this evidence ID is registered to another case in policy_engine (to detect cross-case ID manipulation attempts)
            owner_case = self.policy_engine.resource_case_map.get(evidence_id)
            if owner_case and owner_case != case_id:
                self._verify_auth(
                    actor=actor,
                    action="READ_EVIDENCE",
                    resource_id=evidence_id,
                    target_case_id=case_id,
                    resource_owner_case_id=owner_case
                )
            return None

        # Verify case binding
        if evidence.case_id != case_id:
            # Trigger ID manipulation authorization check which will DENY
            self._verify_auth(
                actor=actor,
                action="READ_EVIDENCE",
                resource_id=evidence_id,
                target_case_id=case_id,
                resource_owner_case_id=evidence.case_id
            )
            return None

        self._verify_auth(
            actor=actor,
            action="READ_EVIDENCE",
            resource_id=evidence_id,
            target_case_id=case_id,
            resource_owner_case_id=evidence.case_id
        )

        # Record access audit event
        self.audit_service.record_event(
            actor_id=actor.sub,
            actor_role=actor.role.value,
            case_id=case_id,
            action="EVIDENCE_ACCESSED",
            target_resource=f"evidence:{evidence_id}",
            decision="ALLOW"
        )
        return evidence

    def list_case_evidence(self, actor: TokenPayload, case_id: str) -> List[Evidence]:
        # Verify read case authorization
        case = self.case_service.get_case(actor, case_id)
        if not case:
            return []
        return self.repository.list_by_case(case_id)

    def verify_evidence_integrity(self, actor: TokenPayload, case_id: str, evidence_id: str) -> EvidenceVerifyResponse:
        evidence = self.repository.get_by_id(evidence_id)
        if not evidence or evidence.case_id != case_id:
            raise KeyError("Evidence reference not found.")

        self._verify_auth(
            actor=actor,
            action="VERIFY_EVIDENCE",
            resource_id=evidence_id,
            target_case_id=case_id,
            resource_owner_case_id=evidence.case_id
        )

        # Recalculate SHA-256 directly from preserved disk file
        actual_sha256 = self.storage.calculate_stored_sha256(evidence.storage_reference)
        now = time.time()

        integrity = IntegrityStatus.INTACT if actual_sha256 == evidence.sha256 else IntegrityStatus.MISMATCH
        preservation = PreservationStatus.VERIFIED if integrity == IntegrityStatus.INTACT else PreservationStatus.CORRUPTED

        evidence.integrity_status = integrity
        evidence.preservation_status = preservation
        self.repository.save(evidence)

        # Audit Event
        self.audit_service.record_event(
            actor_id=actor.sub,
            actor_role=actor.role.value,
            case_id=case_id,
            action="EVIDENCE_INTEGRITY_VERIFIED",
            target_resource=f"evidence:{evidence_id}",
            decision="ALLOW" if integrity == IntegrityStatus.INTACT else "DENY",
            metadata={"expected": evidence.sha256, "calculated": actual_sha256}
        )

        return EvidenceVerifyResponse(
            evidence_id=evidence_id,
            case_id=case_id,
            expected_sha256=evidence.sha256,
            calculated_sha256=actual_sha256,
            integrity_status=integrity,
            verified_at=now,
            verified_by=actor.sub
        )
