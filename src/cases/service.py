"""
Case Domain Service for CRIMENET.
Orchestrates Case Repository, Policy Engine Authorization, and Audit Trail Logging.
"""

import time
import uuid
from typing import Optional, List, Dict, Any

from src.auth.models import TokenPayload
from src.auth.service import AuthService
from src.authorization.policy_engine import PolicyEngine, AuthorizationRequest
from src.audit.service import AuditService
from src.cases.models import Case, CaseStatus, CaseCreate, CaseUpdate, JudicialCaseContext, CaseAnchor, AnchorRole
from src.cases.repository import CaseRepository, SQLiteCaseRepository, InMemoryCaseRepository


class CaseService:
    def __init__(
        self,
        repository: Optional[CaseRepository] = None,
        policy_engine: Optional[PolicyEngine] = None,
        audit_service: Optional[AuditService] = None,
        auth_service: Optional[AuthService] = None
    ):
        self.repository = repository or SQLiteCaseRepository()
        self.policy_engine = policy_engine or PolicyEngine()
        self.audit_service = audit_service or AuditService()
        self.auth_service = auth_service or AuthService()
        self._seed_default_cases()

    def _seed_default_cases(self):
        existing_ids = {c.case_id for c in self.repository.list_all()}
        if "CASE-2026-001" not in existing_ids:
            c1 = Case(
                case_id="CASE-2026-001",
                case_name="Operation Dark Falcon",
                description="Multi-jurisdictional ransomware and illicit asset transfer investigation.",
                status=CaseStatus.ACTIVE,
                created_by="USER-OFFICER-001",
                created_at=time.time() - 86400,
                updated_at=time.time() - 86400,
                assigned_investigators=["USER-OFFICER-001"],
                anchor=CaseAnchor(
                    anchor_id="ANC-2026-001",
                    canonical_name="Operation Cyber Net Target",
                    role=AnchorRole.INVESTIGATION_SUBJECT,
                    description="Primary target subject of cyber financial network inquiry."
                )
            )
            self.repository.save(c1)
        if "CASE-2026-002" not in existing_ids:
            c2 = Case(
                case_id="CASE-2026-002",
                case_name="Operation Red Horizon",
                description="Cross-border contraband trade investigation.",
                status=CaseStatus.ACTIVE,
                created_by="USER-OFFICER-002",
                created_at=time.time() - 43200,
                updated_at=time.time() - 43200,
                assigned_investigators=["USER-OFFICER-002"],
                anchor=CaseAnchor(
                    anchor_id="ANC-2026-002",
                    canonical_name="Operation Red Horizon Complainant",
                    role=AnchorRole.VICTIM,
                    description="Complainant in contraband smuggling case."
                )
            )
            self.repository.save(c2)
        if "CASE-2026-003" not in existing_ids:
            c3 = Case(
                case_id="CASE-2026-003",
                case_name="Operation Closed Vault",
                description="Archived money laundering inquiry.",
                status=CaseStatus.CLOSED,
                created_by="USER-BOSS-001",
                created_at=time.time() - 172800,
                updated_at=time.time() - 172800,
                assigned_investigators=["USER-BOSS-001"],
                anchor=CaseAnchor(
                    anchor_id="ANC-2026-003",
                    canonical_name="Operation Closed Vault Lead",
                    role=AnchorRole.OTHER,
                    description="Archived reference subject."
                )
            )
            self.repository.save(c3)

    def _verify_auth(
        self,
        actor: TokenPayload,
        action: str,
        resource_id: str,
        target_case_id: str,
        context: Optional[Dict[str, Any]] = None
    ):
        user = self.auth_service.get_user_by_id(actor.sub)
        user_authorized_cases = user.authorized_case_ids if user else []

        req = AuthorizationRequest(
            actor=actor,
            action=action,
            resource_type="case",
            resource_id=resource_id,
            target_case_id=target_case_id,
            context=context
        )

        decision = self.policy_engine.evaluate(req, user_authorized_cases)

        # Audit Event Logging
        self.audit_service.record_event(
            actor_id=actor.sub,
            actor_role=actor.role.value,
            case_id=target_case_id,
            action=action,
            target_resource=f"case:{resource_id}",
            decision="ALLOW" if decision.allowed else "DENY",
            metadata={"reason": decision.reason}
        )

        if not decision.allowed:
            raise PermissionError(decision.reason)

    def create_case(self, actor: TokenPayload, create_req: CaseCreate) -> Case:
        temp_id = f"CASE-{time.strftime('%Y')}-{uuid.uuid4().hex[:4].upper()}"

        self._verify_auth(
            actor=actor,
            action="CREATE_CASE",
            resource_id=temp_id,
            target_case_id=temp_id
        )

        assigned = list(set(create_req.assigned_investigators + [actor.sub]))
        now = time.time()

        case = Case(
            case_id=temp_id,
            case_name=create_req.case_name,
            description=create_req.description,
            status=CaseStatus.DRAFT,
            created_by=actor.sub,
            created_at=now,
            updated_at=now,
            judicial_context=create_req.judicial_context,
            assigned_investigators=assigned
        )

        # Update creator's authorized cases list in AuthService and persist
        self.auth_service.authorize_user_for_case(actor.sub, temp_id)

        self.repository.save(case)
        return case

    def list_cases(self, actor: TokenPayload) -> List[Case]:
        all_cases = self.repository.list_all()
        authorized_cases = []
        for c in all_cases:
            try:
                self._verify_auth(
                    actor=actor,
                    action="READ_CASE",
                    resource_id=c.case_id,
                    target_case_id=c.case_id
                )
                authorized_cases.append(c)
            except PermissionError:
                continue
        return authorized_cases

    def get_case(self, actor: TokenPayload, case_id: str) -> Optional[Case]:
        case = self.repository.get_by_id(case_id)
        if not case:
            return None

        self._verify_auth(
            actor=actor,
            action="READ_CASE",
            resource_id=case_id,
            target_case_id=case_id
        )
        return case

    def update_case(self, actor: TokenPayload, case_id: str, update_req: CaseUpdate) -> Optional[Case]:
        case = self.repository.get_by_id(case_id)
        if not case:
            return None

        ctx = {"target_case_status": case.status.value}

        # Check action permissions
        action = "UPDATE_CASE"
        if update_req.judicial_context is not None and update_req.judicial_context != case.judicial_context:
            action = "ASSIGN_JUDICIAL_CONTEXT"

        self._verify_auth(
            actor=actor,
            action=action,
            resource_id=case_id,
            target_case_id=case_id,
            context=ctx
        )

        if update_req.case_name is not None:
            case.case_name = update_req.case_name
        if update_req.description is not None:
            case.description = update_req.description
        if update_req.status is not None:
            case.status = update_req.status
        if update_req.judicial_context is not None:
            case.judicial_context = update_req.judicial_context
        if update_req.assigned_investigators is not None:
            case.assigned_investigators = update_req.assigned_investigators

        case.updated_at = time.time()
        self.repository.save(case)
        return case

    def reopen_case(self, actor: TokenPayload, case_id: str) -> Optional[Case]:
        case = self.repository.get_by_id(case_id)
        if not case:
            return None

        ctx = {"target_case_status": case.status.value}

        self._verify_auth(
            actor=actor,
            action="REOPEN_CASE",
            resource_id=case_id,
            target_case_id=case_id,
            context=ctx
        )

        case.status = CaseStatus.ACTIVE
        case.updated_at = time.time()
        self.repository.save(case)
        return case

    def delete_case(self, actor: TokenPayload, case_id: str) -> bool:
        case = self.repository.get_by_id(case_id)
        if not case:
            return False

        ctx = {"target_case_status": case.status.value}

        self._verify_auth(
            actor=actor,
            action="DELETE_CASE",
            resource_id=case_id,
            target_case_id=case_id,
            context=ctx
        )

        # 1. Clean up file storage directories on disk
        import shutil
        import sqlite3
        from pathlib import Path

        for base_path in ["DATA/evidence_store", "DATA/processing_output", "DATA/staging"]:
            p = Path(base_path) / case_id
            if p.exists():
                shutil.rmtree(p, ignore_errors=True)

        # 2. Delete case metadata from repository
        deleted = self.repository.delete(case_id)

        # 3. Clean up related database records in DATA/cases.db (artifacts, evidence, processing_jobs)
        try:
            cases_db = Path("DATA/cases.db")
            if cases_db.exists():
                with sqlite3.connect(str(cases_db)) as conn:
                    conn.execute("DELETE FROM artifacts WHERE case_id = ?;", (case_id,))
                    conn.execute("DELETE FROM evidence WHERE case_id = ?;", (case_id,))
                    conn.execute("DELETE FROM processing_jobs WHERE case_id = ?;", (case_id,))
                    conn.commit()
        except Exception:
            pass

        # 4. Clean up parsed artifacts in DATA/parsed_artifacts.db
        try:
            parsed_db = Path("DATA/parsed_artifacts.db")
            if parsed_db.exists():
                with sqlite3.connect(str(parsed_db)) as conn:
                    conn.execute("DELETE FROM parsed_artifacts WHERE case_id = ?;", (case_id,))
                    conn.commit()
        except Exception:
            pass

        # 5. Clean up PolicyEngine resource mappings for this case
        purged_resources = [k for k, v in self.policy_engine.resource_case_map.items() if v == case_id]
        for r in purged_resources:
            self.policy_engine.resource_case_map.pop(r, None)
        if hasattr(self.policy_engine, "db_path") and self.policy_engine.db_path and self.policy_engine.db_path != ":memory:":
            try:
                import sqlite3
                conn = sqlite3.connect(self.policy_engine.db_path)
                conn.execute("DELETE FROM resource_case_bindings WHERE case_id = ?", (case_id,))
                conn.commit()
                conn.close()
            except Exception:
                pass

        # 6. Update all users' authorized cases list in AuthService and persist revocation
        for user in getattr(self.auth_service, "_user_db", {}).values():
            if hasattr(self.auth_service, "revoke_user_case"):
                self.auth_service.revoke_user_case(user.user_id, case_id)
            elif case_id in user.authorized_case_ids:
                user.authorized_case_ids.remove(case_id)

        # 7. Audit Log
        self.audit_service.record_event(
            actor_id=actor.sub,
            actor_role=actor.role.value,
            case_id=case_id,
            action="DELETE_CASE",
            target_resource=f"case:{case_id}",
            decision="ALLOW" if deleted else "DENY"
        )

        return deleted
