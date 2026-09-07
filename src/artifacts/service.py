"""
Artifact Service Implementation for CRIMENET (Slice 6).
Handles EvidenceContract_v1 artifact ingestion, deterministic categorization,
idempotent deduplication, PolicyEngine BOLA authorization, and secure content path resolution.
"""

import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from src.auth.models import TokenPayload
from src.auth.service import AuthService
from src.authorization.policy_engine import PolicyEngine, AuthorizationRequest
from src.audit.service import AuditService
from src.artifacts.models import (
    Artifact,
    ArtifactCategory,
    AllocationStatus,
    RecoveryStatus,
    ViewerType,
    ProvenanceEnvelope,
    ArtifactFilterParams
)
from src.artifacts.repository import ArtifactRepository, SQLiteArtifactRepository


class ArtifactService:
    def __init__(
        self,
        repository: Optional[ArtifactRepository] = None,
        policy_engine: Optional[PolicyEngine] = None,
        audit_service: Optional[AuditService] = None,
        auth_service: Optional[AuthService] = None,
        storage_base_dir: str = "DATA/processing_output"
    ):
        self.repository = repository or SQLiteArtifactRepository()
        self.policy_engine = policy_engine or PolicyEngine()
        self.audit_service = audit_service or AuditService()
        self.auth_service = auth_service or AuthService()
        self.storage_base_dir = Path(storage_base_dir).resolve()

    def _verify_auth(
        self,
        actor: TokenPayload,
        action: str,
        resource_id: str,
        target_case_id: str,
        resource_owner_case_id: Optional[str] = None
    ):
        user = self.auth_service.get_user_by_id(actor.sub)
        user_authorized_cases = user.authorized_case_ids if user else []

        req = AuthorizationRequest(
            actor=actor,
            action=action,
            resource_type="artifact",
            resource_id=resource_id,
            target_case_id=target_case_id,
            resource_owner_case_id=resource_owner_case_id
        )

        decision = self.policy_engine.evaluate(req, user_authorized_cases)

        self.audit_service.record_event(
            actor_id=actor.sub,
            actor_role=actor.role.value,
            case_id=target_case_id,
            action=action,
            target_resource=f"artifact:{resource_id}",
            decision="ALLOW" if decision.allowed else "DENY",
            metadata={"reason": decision.reason}
        )

        if not decision.allowed:
            raise PermissionError(decision.reason)

    @staticmethod
    def classify_artifact(
        filename: str,
        raw_type: str,
        raw_mime: Optional[str] = None
    ) -> Tuple[ArtifactCategory, str, str, ViewerType]:
        """
        Determines Layer 1 file category, MIME type, file extension, and recommended viewer interface.
        Note: Does NOT create intelligence entities.
        """
        ext = Path(filename).suffix.lower()
        if not ext and raw_type:
            if raw_type == "PARTITION_TABLE":
                ext = ".hdr"
            elif raw_type == "DATABASE":
                ext = ".db"

        # Defaults
        category = ArtifactCategory.OTHER
        mime_type = raw_mime or "application/octet-stream"
        viewer = ViewerType.HEX

        if raw_type == "PARTITION_TABLE":
            category = ArtifactCategory.PARTITION_TABLE
            mime_type = "application/x-partition-table"
            viewer = ViewerType.HEX
        elif ext in ['.db', '.sqlite', '.sqlite3'] or raw_type == "DATABASE":
            category = ArtifactCategory.DATABASE
            mime_type = "application/x-sqlite3"
            viewer = ViewerType.DATABASE
        elif ext in ['.pdf'] or raw_type == "DOCUMENT":
            category = ArtifactCategory.DOCUMENT
            mime_type = "application/pdf"
            viewer = ViewerType.PDF
        elif ext in ['.doc', '.docx', '.rtf', '.txt']:
            category = ArtifactCategory.DOCUMENT
            mime_type = "text/plain" if ext == '.txt' else "application/msword"
            viewer = ViewerType.TEXT
        elif ext in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.webp'] or raw_type == "IMAGE":
            category = ArtifactCategory.IMAGE
            sub_mime = "jpeg" if ext in ['.jpg', '.jpeg'] else (ext.replace('.', '') if ext else 'jpeg')
            mime_type = f"image/{sub_mime}"
            viewer = ViewerType.IMAGE
        elif ext in ['.eml', '.msg', '.mbox'] or raw_type == "EMAIL":
            category = ArtifactCategory.EMAIL
            mime_type = "message/rfc822"
            viewer = ViewerType.EMAIL
        elif ext in ['.log'] or raw_type == "LOG":
            category = ArtifactCategory.LOG
            mime_type = "text/plain"
            viewer = ViewerType.TEXT
        elif ext in ['.xlsx', '.xls', '.csv'] or raw_type == "SPREADSHEET" or raw_type == "CDR":
            category = ArtifactCategory.CDR if raw_type == "CDR" else ArtifactCategory.SPREADSHEET
            mime_type = "text/csv" if ext == '.csv' else "application/vnd.ms-excel"
            viewer = ViewerType.SPREADSHEET
        elif ext in ['.mp4', '.avi', '.mp3', '.wav'] or raw_type == "MEDIA":
            category = ArtifactCategory.MEDIA
            mime_type = "video/mp4" if ext == '.mp4' else "audio/wav"
            viewer = ViewerType.MEDIA
        elif ext in ['.raw', '.e01', '.e02', '.dd', '.img'] or raw_type == "FORENSIC_IMAGE":
            category = ArtifactCategory.FORENSIC_IMAGE
            mime_type = "application/x-forensic-image"
            viewer = ViewerType.HEX
        elif raw_type == "RECOVERED_FILE":
            category = ArtifactCategory.RECOVERED_FILE
            mime_type = "application/octet-stream"
            viewer = ViewerType.HEX

        return category, mime_type, ext, viewer

    def ingest_contract_artifacts(
        self,
        contract_v1: Dict[str, Any],
        processing_job: Any
    ) -> List[Artifact]:
        """
        Consumes observed artifacts directly from EvidenceContract_v1.
        Deterministically maps observations into classified Artifact domain models.
        Guarantees idempotent deduplication per (case_id, evidence_id, artifact_id).
        """
        provenance = contract_v1.get("provenance_envelope", {})
        case_id = provenance.get("case_id", processing_job.case_id)
        evidence_id = provenance.get("evidence_id", processing_job.evidence_id)
        job_id = provenance.get("processing_job_id", processing_job.job_id)
        engine_name = provenance.get("engine_name", processing_job.engine_name)
        engine_version = provenance.get("engine_version", processing_job.engine_version)

        raw_artifacts = contract_v1.get("observed_artifacts", [])
        ingested_artifacts: List[Artifact] = []

        for raw_art in raw_artifacts:
            # Source artifact ID or deterministic hash derivation
            source_art_id = raw_art.get("artifact_id")
            name = raw_art.get("artifact_name", "unnamed_artifact")
            raw_type = raw_art.get("artifact_type", "OTHER")
            provenance_trace = raw_art.get("provenance_trace", f"{job_id}:{source_art_id}")

            if not source_art_id:
                # Deterministic artifact ID if missing from raw source
                hash_input = f"{case_id}:{evidence_id}:{job_id}:{name}:{provenance_trace}"
                det_suffix = hashlib.sha256(hash_input.encode()).hexdigest()[:8].upper()
                art_id = f"ART-{case_id.replace('CASE-', '')}-{det_suffix}"
            else:
                art_id = source_art_id

            category, mime_type, ext, viewer = self.classify_artifact(name, raw_type, raw_art.get("mime_type"))

            # Allocation status handling (Strict evidence check)
            raw_alloc = raw_art.get("allocation_status")
            if raw_alloc and raw_alloc in AllocationStatus.__members__:
                alloc_status = AllocationStatus(raw_alloc)
            elif raw_type == "DELETED_FILE":
                alloc_status = AllocationStatus.DELETED
            elif raw_art.get("is_deleted") is True:
                alloc_status = AllocationStatus.DELETED
            elif raw_art.get("is_deleted") is False:
                alloc_status = AllocationStatus.ALLOCATED
            else:
                alloc_status = AllocationStatus.ALLOCATED  # Default for observed system headers/MBR

            # Recovery status handling (Strict evidence check)
            raw_rec = raw_art.get("recovery_status")
            if raw_rec and raw_rec in RecoveryStatus.__members__:
                rec_status = RecoveryStatus(raw_rec)
            elif raw_type == "RECOVERED_FILE" or raw_art.get("is_recovered") is True:
                rec_status = RecoveryStatus.RECOVERED
            elif raw_art.get("is_carved") is True:
                rec_status = RecoveryStatus.CARVED
            else:
                rec_status = RecoveryStatus.NONE

            prov_envelope = ProvenanceEnvelope(
                case_id=case_id,
                evidence_id=evidence_id,
                processing_job_id=job_id,
                engine_name=engine_name,
                engine_version=engine_version,
                source_reference=f"EV-{evidence_id}",
                observation_reference=provenance_trace
            )

            # Build server-controlled safe content reference if relative path provided
            rel_content = raw_art.get("content_path") or raw_art.get("extracted_path")
            if not rel_content:
                rel_content = f"{case_id}/{job_id}/{art_id}{ext}"

            artifact = Artifact(
                artifact_id=art_id,
                case_id=case_id,
                evidence_id=evidence_id,
                processing_job_id=job_id,
                filename=name,
                path_within_source=provenance_trace,
                category=category,
                mime_type=mime_type,
                file_extension=ext,
                size_bytes=raw_art.get("size_bytes", 0),
                sha256=raw_art.get("sha256"),
                created_at_observed=raw_art.get("created_at"),
                modified_at_observed=raw_art.get("modified_at"),
                accessed_at_observed=raw_art.get("accessed_at"),
                allocation_status=alloc_status,
                recovery_status=rec_status,
                observation_method=raw_art.get("observation_method", "FILE_SYSTEM_PARSE"),
                recommended_viewer=viewer,
                provenance_chain=prov_envelope,
                content_reference=rel_content
            )

            self.repository.save(artifact)
            ingested_artifacts.append(artifact)

        return ingested_artifacts

    def list_case_artifacts(
        self,
        actor: TokenPayload,
        case_id: str,
        filters: Optional[ArtifactFilterParams] = None
    ) -> List[Artifact]:
        """Lists all artifacts belonging to an authorized case."""
        self._verify_auth(
            actor=actor,
            action="VIEW_CASE_ARTIFACTS",
            resource_id=f"case:{case_id}",
            target_case_id=case_id
        )
        return self.repository.list_by_case(case_id, filters)

    def get_artifact(
        self,
        actor: TokenPayload,
        case_id: str,
        artifact_id: str
    ) -> Optional[Artifact]:
        """Retrieves single artifact metadata after checking BOLA authorization."""
        artifact = self.repository.get_by_id(artifact_id)
        if not artifact:
            return None

        # BOLA Check: Ensure artifact case matches URL case_id
        if artifact.case_id != case_id:
            raise PermissionError(f"ID MANIPULATION DENY: Artifact '{artifact_id}' belongs to case '{artifact.case_id}', not '{case_id}'.")

        self._verify_auth(
            actor=actor,
            action="VIEW_ARTIFACT",
            resource_id=artifact_id,
            target_case_id=case_id,
            resource_owner_case_id=artifact.case_id
        )

        return artifact

    def get_artifact_content_path(
        self,
        actor: TokenPayload,
        case_id: str,
        artifact_id: str
    ) -> Path:
        """
        Resolves content file path safely after BOLA authorization.
        Strictly canonicalizes paths and rejects path traversal, UNC, Windows drive absolute paths,
        or any attempt to escape server storage boundaries.
        """
        artifact = self.get_artifact(actor, case_id, artifact_id)
        if not artifact:
            raise KeyError(f"Artifact '{artifact_id}' not found under case '{case_id}'.")

        if not artifact.content_reference:
            raise ValueError(f"Artifact '{artifact_id}' has no content reference.")

        content_ref = artifact.content_reference

        # PATH TRAVERSAL DEFENSE CHECKS
        if any(seq in content_ref for seq in ["..", "/etc/", "C:", "c:", "\\", "file://", "http://", "https://"]):
            raise PermissionError(f"PATH TRAVERSAL DENIED: Illegal path sequence in content reference '{content_ref}'.")

        # Resolve candidate path relative to server storage base directory
        candidate_path = (self.storage_base_dir / content_ref).resolve()
        base_dir_resolved = self.storage_base_dir.resolve()

        # Enforce canonical boundary check
        try:
            candidate_path.relative_to(base_dir_resolved)
        except ValueError:
            raise PermissionError(f"PATH TRAVERSAL DENIED: Path '{candidate_path}' escapes base directory '{base_dir_resolved}'.")

        return candidate_path
