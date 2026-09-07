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
        # Pre-seed baseline test cases matching Slice 1 auth tests
        c1 = Case(
            case_id="CASE-2026-001",
            case_name="Operation Cyber Net",
            description="Investigation into illicit cyber financial network.",
            status=CaseStatus.ACTIVE,
            created_by="USER-OFFICER-001",
            created_at=time.time() - 86400,
            updated_at=time.time() - 86400,
            judicial_context=JudicialCaseContext(
                court_judge_id="USER-JUDGE-001",
                court_level="SPECIFIC_COURT",
                court_reference="COURT-DL-001",
                judicial_case_reference="CR-2026-9981"
            ),
            assigned_investigators=["USER-OFFICER-001"],
            anchor=CaseAnchor(
                anchor_id="ANC-2026-001",
                canonical_name="Operation Cyber Net Target",
                role=AnchorRole.INVESTIGATION_SUBJECT,
                description="Primary target subject of cyber financial network inquiry."
            )
        )
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
        self.repository.save(c1)
        self.repository.save(c2)
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

        # Update creator's authorized cases list in AuthService
        user = self.auth_service.get_user_by_id(actor.sub)
        if user and temp_id not in user.authorized_case_ids:
            user.authorized_case_ids.append(temp_id)

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

        # 1. Clean up file storage directories
        import shutil
        from pathlib import Path
        ev_store = Path("DATA/evidence_store") / case_id
        if ev_store.exists():
            shutil.rmtree(ev_store, ignore_errors=True)
        proc_out = Path("DATA/processing_output") / case_id
        if proc_out.exists():
            shutil.rmtree(proc_out, ignore_errors=True)

        # 2. Delete from repository
        deleted = self.repository.delete(case_id)

        # 3. Update user's authorized cases list in AuthService
        user = self.auth_service.get_user_by_id(actor.sub)
        if user and case_id in user.authorized_case_ids:
            user.authorized_case_ids.remove(case_id)

        # 4. Audit Log
        self.audit_service.record_event(
            actor_id=actor.sub,
            actor_role=actor.role.value,
            case_id=case_id,
            action="DELETE_CASE",
            target_resource=f"case:{case_id}",
            decision="ALLOW" if deleted else "DENY"
        )

        return deleted
