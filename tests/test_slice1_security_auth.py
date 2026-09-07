"""
Comprehensive Security and Adversarial Test Suite for CRIMENET Slice 1.
Tests Authentication, RBAC, Policy Engine, BOLA, BFLA, Role/Court Scope, ID Manipulation, and Audit Hash Chain Integrity.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.auth.service import AuthService
from src.auth.models import UserRole, CourtLevel, JudicialContext, User
from src.authorization.policy_engine import PolicyEngine, AuthorizationRequest
from src.audit.service import AuditService
from src.integrity.provider import LocalCryptoChainIntegrityProvider

client = TestClient(app)
auth_service = AuthService()


def get_token_for_user(username: str, password: str) -> str:
    res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"Failed login for {username}: {res.json()}"
    return res.json()["access_token"]


# ============================================================================
# 1. AUTHENTICATION & TOKEN INTEGRITY TESTS
# ============================================================================

def test_login_success():
    res = client.post("/api/v1/auth/login", json={"username": "officer1", "password": "OfficerPass123!"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["username"] == "officer1"
    assert data["user"]["role"] == "INVESTIGATION_OFFICER"


def test_login_invalid_password():
    res = client.post("/api/v1/auth/login", json={"username": "officer1", "password": "WrongPassword!"})
    assert res.status_code == 401
    assert "Invalid credentials" in res.json()["detail"]


def test_login_unknown_user():
    res = client.post("/api/v1/auth/login", json={"username": "fake_hacker", "password": "Password123!"})
    assert res.status_code == 401


def test_direct_api_access_without_token():
    res = client.get("/api/v1/cases/CASE-2026-001")
    assert res.status_code == 401
    assert "Missing Authorization Header" in res.json()["detail"]


def test_invalid_token_header_format():
    headers = {"Authorization": "Basic dXNlcjpwYXNz"}
    res = client.get("/api/v1/cases/CASE-2026-001", headers=headers)
    assert res.status_code == 401
    assert "Invalid Authorization Header scheme" in res.json()["detail"]


def test_role_tampering_attack():
    """Adversarial Attack: Modifying role in JWT payload without valid secret signature."""
    token = get_token_for_user("officer1", "OfficerPass123!")
    parts = token.split('.')
    # Hacked token with forged payload changing role to HIGHER_AUTHORITY
    import base64, json
    payload = json.loads(base64.urlsafe_b64decode(parts[1] + '==').decode('utf-8'))
    payload["role"] = "HIGHER_AUTHORITY"
    forged_payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode('utf-8')).decode('utf-8').rstrip('=')
    forged_token = f"{parts[0]}.{forged_payload_b64}.{parts[2]}"

    headers = {"Authorization": f"Bearer {forged_token}"}
    res = client.get("/api/v1/cases/CASE-2026-002", headers=headers)
    assert res.status_code == 401
    assert "Invalid or expired access token" in res.json()["detail"]


# ============================================================================
# 2. OBJECT-LEVEL (BOLA) & HORIZONTAL PRIVILEGE ESCALATION TESTS
# ============================================================================

def test_authorized_case_access_allowed():
    token = get_token_for_user("officer1", "OfficerPass123!")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/cases/CASE-2026-001", headers=headers)
    assert res.status_code == 200
    assert res.json()["case_id"] == "CASE-2026-001"


def test_horizontal_privilege_escalation_denied():
    """Adversarial Attack: User A changing case ID to User B's authorized case."""
    token = get_token_for_user("officer1", "OfficerPass123!")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/cases/CASE-2026-002", headers=headers)
    assert res.status_code == 403
    assert "Officer not authorized for case" in res.json()["detail"]


def test_evidence_id_manipulation_denied():
    """Adversarial Attack: Requesting evidence ID belonging to another case."""
    token = get_token_for_user("officer1", "OfficerPass123!")
    headers = {"Authorization": f"Bearer {token}"}
    # EV-2026-9004 belongs to CASE-2026-002, but hacker requests it under CASE-2026-001
    res = client.get("/api/v1/cases/CASE-2026-001/evidence/EV-2026-9004", headers=headers)
    assert res.status_code == 403
    assert "ID MANIPULATION DENY" in res.json()["detail"]


def test_report_id_manipulation_denied():
    """Adversarial Attack: Requesting report ID belonging to another case."""
    token = get_token_for_user("officer1", "OfficerPass123!")
    headers = {"Authorization": f"Bearer {token}"}
    # REP-2026-002 belongs to CASE-2026-002, but hacker requests it under CASE-2026-001
    res = client.get("/api/v1/cases/CASE-2026-001/reports/REP-2026-002", headers=headers)
    assert res.status_code == 403
    assert "ID MANIPULATION DENY" in res.json()["detail"]


# ============================================================================
# 3. FUNCTION-LEVEL (BFLA) & VERTICAL PRIVILEGE ESCALATION TESTS
# ============================================================================

def test_vertical_escalation_judicial_override_denied():
    """Adversarial Attack: Officer attempting to issue judicial warrant override."""
    token = get_token_for_user("officer1", "OfficerPass123!")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.post("/api/v1/cases/CASE-2026-001/judicial_override", headers=headers)
    assert res.status_code == 403
    assert "cannot issue judicial overrides" in res.json()["detail"]


def test_vertical_escalation_audit_logs_denied():
    """Adversarial Attack: Officer attempting to inspect global audit logs."""
    token = get_token_for_user("officer1", "OfficerPass123!")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/audit/logs", headers=headers)
    assert res.status_code == 403
    assert "lacks permission to access audit logs" in res.json()["detail"]


def test_higher_authority_audit_logs_allowed():
    token = get_token_for_user("boss1", "HigherAuthPass789!")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/audit/logs", headers=headers)
    assert res.status_code == 200
    assert res.json()["integrity_chain_valid"] is True


def test_higher_authority_cross_case_access():
    token = get_token_for_user("boss1", "HigherAuthPass789!")
    headers = {"Authorization": f"Bearer {token}"}
    res1 = client.get("/api/v1/cases/CASE-2026-001", headers=headers)
    res2 = client.get("/api/v1/cases/CASE-2026-002", headers=headers)
    assert res1.status_code == 200
    assert res2.status_code == 200


# ============================================================================
# 4. COURT JUDGE & JURISDICTIONAL SCOPE TESTS
# ============================================================================

def test_judge_specific_court_scope():
    token = get_token_for_user("judge_specific", "JudgePass001!")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Authorized case
    res1 = client.get("/api/v1/cases/CASE-2026-001", headers=headers)
    assert res1.status_code == 200
    
    # Unauthorized case for specific court judge
    res2 = client.get("/api/v1/cases/CASE-2026-002", headers=headers)
    assert res2.status_code == 403
    assert "Specific Court judge not assigned to case" in res2.json()["detail"]


def test_judge_high_court_scope():
    token = get_token_for_user("judge_high", "JudgePass002!")
    headers = {"Authorization": f"Bearer {token}"}
    res1 = client.get("/api/v1/cases/CASE-2026-001", headers=headers)
    res2 = client.get("/api/v1/cases/CASE-2026-002", headers=headers)
    assert res1.status_code == 200
    assert res2.status_code == 200


def test_judge_supreme_court_scope():
    token = get_token_for_user("judge_supreme", "JudgePass003!")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/cases/CASE-2026-003", headers=headers)
    assert res.status_code == 200


def test_judge_judicial_override_allowed():
    token = get_token_for_user("judge_supreme", "JudgePass003!")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.post("/api/v1/cases/CASE-2026-001/judicial_override", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "WARRANT_GRANTED"


# ============================================================================
# 5. AUDIT LOG CRYPTOGRAPHIC HASH CHAIN TAMPERING TEST
# ============================================================================

def test_audit_hash_chain_integrity_verification():
    audit_svc = AuditService()
    
    # Record 3 events
    e1 = audit_svc.record_event("officer1", "INVESTIGATION_OFFICER", "CASE-2026-001", "READ_CASE", "case:CASE-2026-001", "ALLOW")
    e2 = audit_svc.record_event("officer1", "INVESTIGATION_OFFICER", "CASE-2026-002", "READ_CASE", "case:CASE-2026-002", "DENY")
    e3 = audit_svc.record_event("boss1", "HIGHER_AUTHORITY", "CASE-2026-002", "READ_CASE", "case:CASE-2026-002", "ALLOW")

    # Verify initial valid chain
    assert audit_svc.verify_integrity() is True

    # Adversarial Attack: Tamper with action in second event
    audit_svc.audit_log[1].action = "READ_CONFIDENTIAL_REPORT"

    # Verify chain detects tampering
    assert audit_svc.verify_integrity() is False
