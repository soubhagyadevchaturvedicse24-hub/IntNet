"""
Deep Parsing Service for CRIMENET (Slice 8A).
Orchestrates deep inspection of forensic artifacts with:
- Server-side PolicyEngine BOLA/BFLA authorization
- Case-scoped boundary validation and ID manipulation defense
- Safe content path resolution (rejecting any client-supplied paths)
- Magic-byte driven parser dispatch
- Strict isolation (isolated parser errors never cascade into pipeline failure)
- Provenance tracking and idempotent caching
- ZERO automatic graph insertion (strictly decoupled from Kùzu graph in Slice 8A)
"""

from pathlib import Path
from typing import Optional, List, Dict, Any

from src.auth.models import TokenPayload
from src.auth.service import AuthService
from src.authorization.policy_engine import PolicyEngine, AuthorizationRequest
from src.audit.service import AuditService
from src.artifacts.service import ArtifactService
from src.parsers.models import ParsedArtifact, ParsingStatus
from src.parsers.registry import ParserRegistry
from src.parsers.repository import SQLiteParsedArtifactRepository


class DeepParsingService:
    """
    Core service coordinating deep artifact inspection and observation extraction.
    """

    def __init__(
        self,
        artifact_service: Optional[ArtifactService] = None,
        repository: Optional[SQLiteParsedArtifactRepository] = None,
        registry: Optional[ParserRegistry] = None,
        policy_engine: Optional[PolicyEngine] = None,
        audit_service: Optional[AuditService] = None,
        auth_service: Optional[AuthService] = None,
    ):
        self.artifact_service = artifact_service or ArtifactService()
        self.repository = repository or SQLiteParsedArtifactRepository()
        self.registry = registry or ParserRegistry()
        self.policy_engine = policy_engine or PolicyEngine()
        self.audit_service = audit_service or AuditService()
        self.auth_service = auth_service or AuthService()

    def _verify_auth(
        self,
        actor: TokenPayload,
        action: str,
        resource_id: str,
        target_case_id: str,
        resource_owner_case_id: Optional[str] = None,
    ):
        """Enforces PolicyEngine authorization with audit logging."""
        user = self.auth_service.get_user_by_id(actor.sub)
        user_authorized_cases = user.authorized_case_ids if user else []

        req = AuthorizationRequest(
            actor=actor,
            action=action,
            resource_type="artifact_deep_parsing",
            resource_id=resource_id,
            target_case_id=target_case_id,
            resource_owner_case_id=resource_owner_case_id,
        )

        decision = self.policy_engine.evaluate(req, user_authorized_cases)

        self.audit_service.record_event(
            actor_id=actor.sub,
            actor_role=actor.role.value,
            case_id=target_case_id,
            action=action,
            target_resource=f"artifact_parse:{resource_id}",
            decision="ALLOW" if decision.allowed else "DENY",
            metadata={"reason": decision.reason},
        )

        if not decision.allowed:
            raise PermissionError(decision.reason)

    def parse_artifact(
        self,
        actor: TokenPayload,
        case_id: str,
        artifact_id: str,
        force_reparse: bool = False,
    ) -> ParsedArtifact:
        """
        Executes deep inspection of an artifact.
        Authenticates caller, checks BOLA, safely resolves internal file path,
        and executes format parser. Caches results to prevent redundant expensive parses.
        """
        # 1. Fetch artifact metadata and verify BOLA ownership
        artifact = self.artifact_service.get_artifact(actor=actor, case_id=case_id, artifact_id=artifact_id)
        if not artifact:
            raise KeyError(f"Artifact '{artifact_id}' not found under case '{case_id}'.")

        if artifact.case_id != case_id:
            raise PermissionError(
                f"ID MANIPULATION DENIED: Artifact '{artifact_id}' belongs to case '{artifact.case_id}', not '{case_id}'."
            )

        # 2. Authorize parsing action
        self._verify_auth(
            actor=actor,
            action="VIEW_ARTIFACT",  # Investigators with artifact view permission can inspect
            resource_id=artifact_id,
            target_case_id=case_id,
            resource_owner_case_id=artifact.case_id,
        )

        # 3. Check cache (idempotency check)
        if not force_reparse:
            cached = self.repository.get_by_id(artifact_id)
            if cached and cached.computed_sha256 == artifact.sha256:
                return cached

        # 4. Resolve safe internal storage path (Client cannot supply path!)
        file_path = self.artifact_service.get_artifact_content_path(
            actor=actor, case_id=case_id, artifact_id=artifact_id
        )

        # 5. Dispatch to parser based on header magic bytes
        parser = self.registry.get_parser_for_file(file_path)

        artifact_dict = {
            "artifact_id": artifact.artifact_id,
            "case_id": artifact.case_id,
            "filename": artifact.filename,
            "sha256": artifact.sha256,
            "category": artifact.category.value,
        }

        # 6. Execute parse with error isolation
        parsed_result = parser.parse(file_path=file_path, artifact_metadata=artifact_dict)

        # 7. Persist observation record in repository
        self.repository.save(parsed_result)

        # NOTE: Explicitly DO NOT insert into Kùzu graph (strictly deferred to Slice 8C/9)

        return parsed_result

    def get_parsed_artifact(
        self,
        actor: TokenPayload,
        case_id: str,
        artifact_id: str,
    ) -> Optional[ParsedArtifact]:
        """
        Retrieves existing parsed observations from repository after BOLA authorization.
        """
        artifact = self.artifact_service.get_artifact(actor=actor, case_id=case_id, artifact_id=artifact_id)
        if not artifact:
            raise KeyError(f"Artifact '{artifact_id}' not found under case '{case_id}'.")

        if artifact.case_id != case_id:
            raise PermissionError(
                f"ID MANIPULATION DENIED: Artifact '{artifact_id}' belongs to case '{artifact.case_id}', not '{case_id}'."
            )

        self._verify_auth(
            actor=actor,
            action="VIEW_ARTIFACT",
            resource_id=artifact_id,
            target_case_id=case_id,
            resource_owner_case_id=artifact.case_id,
        )

        return self.repository.get_by_id(artifact_id)
