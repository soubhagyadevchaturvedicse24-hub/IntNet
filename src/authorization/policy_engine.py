"""
Centralized Policy Decision Point (PDP) and Policy Enforcement Engine for CRIMENET.
Enforces BOLA, BFLA, Role Capabilities, Judicial Court Scope, Resource Binding, and Closed Case Modification rules.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from src.auth.models import UserRole, CourtLevel, JudicialContext, UserPublic, TokenPayload


class AuthorizationRequest(BaseModel):
    actor: TokenPayload
    action: str  # e.g., "READ_CASE", "CREATE_CASE", "UPDATE_CASE", "CLOSE_CASE", "REOPEN_CASE", "ASSIGN_INVESTIGATOR", "ASSIGN_JUDICIAL_CONTEXT", "READ_EVIDENCE", "READ_REPORT", "JUDICIAL_OVERRIDE", "VIEW_AUDIT_LOGS"
    resource_type: str  # e.g., "case", "evidence", "report", "audit_log"
    resource_id: str
    target_case_id: str
    resource_owner_case_id: Optional[str] = None  # Actual owner case ID of the resource (to prevent ID manipulation)
    context: Optional[Dict[str, Any]] = None


class AuthorizationDecision(BaseModel):
    allowed: bool
    reason: str
    actor_id: str
    action: str
    resource_type: str
    resource_id: str
    target_case_id: str


class PolicyEngine:
    def __init__(self, resource_case_map: Optional[Dict[str, str]] = None):
        # Mock resource registry mapping resource_id -> true_case_id
        self.resource_case_map = resource_case_map or {
            # Evidence
            "EV-2026-9001": "CASE-2026-001",
            "EV-2026-9002": "CASE-2026-001",
            "EV-2026-9003": "CASE-2026-001",
            "EV-2026-9004": "CASE-2026-002",
            "EV-2026-9005": "CASE-2026-002",
            # Reports
            "REP-2026-001": "CASE-2026-001",
            "REP-2026-002": "CASE-2026-002",
            "REP-2026-003": "CASE-2026-003",
        }

    def register_resource_case(self, resource_id: str, case_id: str):
        self.resource_case_map[resource_id] = case_id

    def evaluate(self, req: AuthorizationRequest, user_authorized_cases: List[str]) -> AuthorizationDecision:
        actor = req.actor
        ctx = req.context or {}

        # 1. Role Capabilities Check (BFLA)
        if req.action == "REGISTER_EVIDENCE":
            if actor.role not in [UserRole.INVESTIGATION_OFFICER, UserRole.HIGHER_AUTHORITY]:
                return AuthorizationDecision(
                    allowed=False,
                    reason=f"BFLA DENY: Role '{actor.role}' cannot register evidence.",
                    actor_id=actor.sub,
                    action=req.action,
                    resource_type=req.resource_type,
                    resource_id=req.resource_id,
                    target_case_id=req.target_case_id
                )

        if req.action == "CREATE_CASE":
            if actor.role not in [UserRole.INVESTIGATION_OFFICER, UserRole.HIGHER_AUTHORITY]:
                return AuthorizationDecision(
                    allowed=False,
                    reason=f"BFLA DENY: Role '{actor.role}' cannot create cases.",
                    actor_id=actor.sub,
                    action=req.action,
                    resource_type=req.resource_type,
                    resource_id=req.resource_id,
                    target_case_id=req.target_case_id
                )
            return AuthorizationDecision(
                allowed=True,
                reason="ALLOW: Authorized role case creation granted.",
                actor_id=actor.sub,
                action=req.action,
                resource_type=req.resource_type,
                resource_id=req.resource_id,
                target_case_id=req.target_case_id
            )

        if req.action == "VIEW_AUDIT_LOGS":
            if actor.role not in [UserRole.HIGHER_AUTHORITY, UserRole.COURT_JUDGE]:
                return AuthorizationDecision(
                    allowed=False,
                    reason=f"BFLA DENY: Role '{actor.role}' lacks permission to access audit logs.",
                    actor_id=actor.sub,
                    action=req.action,
                    resource_type=req.resource_type,
                    resource_id=req.resource_id,
                    target_case_id=req.target_case_id
                )

        if req.action == "JUDICIAL_OVERRIDE":
            if actor.role != UserRole.COURT_JUDGE and actor.role != UserRole.HIGHER_AUTHORITY:
                return AuthorizationDecision(
                    allowed=False,
                    reason=f"BFLA DENY: Role '{actor.role}' cannot issue judicial overrides.",
                    actor_id=actor.sub,
                    action=req.action,
                    resource_type=req.resource_type,
                    resource_id=req.resource_id,
                    target_case_id=req.target_case_id
                )

        if req.action in ["ASSIGN_JUDICIAL_CONTEXT", "CHANGE_OWNERSHIP"]:
            if actor.role not in [UserRole.HIGHER_AUTHORITY, UserRole.COURT_JUDGE]:
                return AuthorizationDecision(
                    allowed=False,
                    reason=f"BFLA DENY: Role '{actor.role}' cannot modify ownership or judicial assignment.",
                    actor_id=actor.sub,
                    action=req.action,
                    resource_type=req.resource_type,
                    resource_id=req.resource_id,
                    target_case_id=req.target_case_id
                )

        # 2. Closed Case Modification Protection
        target_status = ctx.get("target_case_status")
        if target_status == "CLOSED":
            if req.action != "REOPEN_CASE":
                return AuthorizationDecision(
                    allowed=False,
                    reason="CLOSED CASE DENY: Modifications to closed cases are prohibited unless reopened.",
                    actor_id=actor.sub,
                    action=req.action,
                    resource_type=req.resource_type,
                    resource_id=req.resource_id,
                    target_case_id=req.target_case_id
                )
            elif actor.role not in [UserRole.HIGHER_AUTHORITY, UserRole.COURT_JUDGE]:
                return AuthorizationDecision(
                    allowed=False,
                    reason=f"BFLA DENY: Role '{actor.role}' cannot reopen a closed case.",
                    actor_id=actor.sub,
                    action=req.action,
                    resource_type=req.resource_type,
                    resource_id=req.resource_id,
                    target_case_id=req.target_case_id
                )

        # 3. Resource ID Binding Validation (ID Manipulation Protection)
        owner_case_id = req.resource_owner_case_id or self.resource_case_map.get(req.resource_id)
        if owner_case_id and owner_case_id != req.target_case_id:
            return AuthorizationDecision(
                allowed=False,
                reason=f"ID MANIPULATION DENY: Resource '{req.resource_id}' belongs to case '{owner_case_id}', not target case '{req.target_case_id}'.",
                actor_id=actor.sub,
                action=req.action,
                resource_type=req.resource_type,
                resource_id=req.resource_id,
                target_case_id=req.target_case_id
            )

        # 4. Case-Level Authorization & Scope Check (BOLA)
        if actor.role == UserRole.HIGHER_AUTHORITY:
            return AuthorizationDecision(
                allowed=True,
                reason="ALLOW: Higher authority cross-case authorization granted.",
                actor_id=actor.sub,
                action=req.action,
                resource_type=req.resource_type,
                resource_id=req.resource_id,
                target_case_id=req.target_case_id
            )

        if actor.role == UserRole.COURT_JUDGE:
            if not actor.judicial_context:
                return AuthorizationDecision(
                    allowed=False,
                    reason="DENY: Court judge missing judicial context.",
                    actor_id=actor.sub,
                    action=req.action,
                    resource_type=req.resource_type,
                    resource_id=req.resource_id,
                    target_case_id=req.target_case_id
                )
            
            court_lvl = actor.judicial_context.court_level
            if court_lvl == CourtLevel.SUPREME_COURT:
                return AuthorizationDecision(
                    allowed=True,
                    reason="ALLOW: Supreme Court national jurisdiction granted.",
                    actor_id=actor.sub,
                    action=req.action,
                    resource_type=req.resource_type,
                    resource_id=req.resource_id,
                    target_case_id=req.target_case_id
                )
            elif court_lvl == CourtLevel.HIGH_COURT:
                return AuthorizationDecision(
                    allowed=True,
                    reason="ALLOW: High Court state jurisdiction granted.",
                    actor_id=actor.sub,
                    action=req.action,
                    resource_type=req.resource_type,
                    resource_id=req.resource_id,
                    target_case_id=req.target_case_id
                )
            elif court_lvl == CourtLevel.SPECIFIC_COURT:
                if "*" not in user_authorized_cases and req.target_case_id not in user_authorized_cases:
                    return AuthorizationDecision(
                        allowed=False,
                        reason=f"BOLA DENY: Specific Court judge not assigned to case '{req.target_case_id}'.",
                        actor_id=actor.sub,
                        action=req.action,
                        resource_type=req.resource_type,
                        resource_id=req.resource_id,
                        target_case_id=req.target_case_id
                    )

        if actor.role == UserRole.INVESTIGATION_OFFICER:
            if "*" not in user_authorized_cases and req.target_case_id not in user_authorized_cases:
                return AuthorizationDecision(
                    allowed=False,
                    reason=f"BOLA DENY: Officer not authorized for case '{req.target_case_id}'.",
                    actor_id=actor.sub,
                    action=req.action,
                    resource_type=req.resource_type,
                    resource_id=req.resource_id,
                    target_case_id=req.target_case_id
                )

        return AuthorizationDecision(
            allowed=True,
            reason="ALLOW: Server-side authorization check passed.",
            actor_id=actor.sub,
            action=req.action,
            resource_type=req.resource_type,
            resource_id=req.resource_id,
            target_case_id=req.target_case_id
        )
