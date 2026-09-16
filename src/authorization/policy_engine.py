"""
Centralized Policy Decision Point (PDP) and Policy Enforcement Engine for CRIMENET.
Enforces BOLA, BFLA, Role Capabilities, Judicial Court Scope, Resource Binding, and Closed Case Modification rules.
"""

import sqlite3
import time
from pathlib import Path
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
    def __init__(self, resource_case_map: Optional[Dict[str, str]] = None, db_path: str = "DATA/cases.db"):
        self.db_path = db_path
        # Seed default mappings
        self.resource_case_map = {
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
        if resource_case_map:
            self.resource_case_map.update(resource_case_map)

        self._init_db()
        self._load_persisted_bindings()

    def _init_db(self):
        if not self.db_path or self.db_path == ":memory:":
            return
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS resource_case_bindings (
                    resource_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
            """)
            conn.commit()
            conn.close()
        except Exception:
            pass

    def _load_persisted_bindings(self):
        if not self.db_path or self.db_path == ":memory:":
            return
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT resource_id, case_id FROM resource_case_bindings")
            for row in cursor.fetchall():
                self.resource_case_map[row["resource_id"]] = row["case_id"]
            conn.close()
        except Exception:
            pass

    def get_resource_case(self, resource_id: str) -> Optional[str]:
        if resource_id in self.resource_case_map:
            return self.resource_case_map[resource_id]
        if self.db_path and self.db_path != ":memory:":
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT case_id FROM resource_case_bindings WHERE resource_id=?", (resource_id,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    self.resource_case_map[resource_id] = row[0]
                    return row[0]
            except Exception:
                pass
        return None

    def register_resource_case(self, resource_id: str, case_id: str, resource_type: str = "general"):
        self.resource_case_map[resource_id] = case_id
        if self.db_path and self.db_path != ":memory:":
            try:
                Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
                conn = sqlite3.connect(self.db_path)
                conn.execute("""
                    INSERT INTO resource_case_bindings (resource_id, case_id, resource_type, created_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(resource_id) DO UPDATE SET
                        case_id = excluded.case_id,
                        resource_type = excluded.resource_type,
                        created_at = excluded.created_at;
                """, (resource_id, case_id, resource_type, time.time()))
                conn.commit()
                conn.close()
            except Exception:
                pass

    def register_resources_batch(self, items: List[Any]):
        """
        High-performance bulk registration of resource-to-case bindings in a single transaction.
        """
        now = time.time()
        for item in items:
            res_id, cid = item[0], item[1]
            self.resource_case_map[res_id] = cid

        if self.db_path and self.db_path != ":memory:":
            try:
                Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
                conn = sqlite3.connect(self.db_path)
                params = [(item[0], item[1], item[2] if len(item) > 2 else "general", now) for item in items]
                conn.executemany("""
                    INSERT INTO resource_case_bindings (resource_id, case_id, resource_type, created_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(resource_id) DO UPDATE SET
                        case_id = excluded.case_id,
                        resource_type = excluded.resource_type,
                        created_at = excluded.created_at;
                """, params)
                conn.commit()
                conn.close()
            except Exception:
                pass

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
            if req.action not in ["REOPEN_CASE", "DELETE_CASE"]:
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
        if not owner_case_id and self.db_path and self.db_path != ":memory:":
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT case_id FROM resource_case_bindings WHERE resource_id = ?", (req.resource_id,))
                row = cursor.fetchone()
                if row:
                    owner_case_id = row["case_id"]
                    self.resource_case_map[req.resource_id] = owner_case_id
                else:
                    cursor.execute("SELECT case_id FROM evidence WHERE evidence_id = ?", (req.resource_id,))
                    row_ev = cursor.fetchone()
                    if row_ev:
                        owner_case_id = row_ev["case_id"]
                        self.resource_case_map[req.resource_id] = owner_case_id
                    else:
                        cursor.execute("SELECT case_id FROM artifacts WHERE artifact_id = ?", (req.resource_id,))
                        row_art = cursor.fetchone()
                        if row_art:
                            owner_case_id = row_art["case_id"]
                            self.resource_case_map[req.resource_id] = owner_case_id
                conn.close()
            except Exception:
                pass
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
