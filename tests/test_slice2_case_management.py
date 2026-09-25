"""
Comprehensive Security and Domain Test Suite for CRIMENET Slice 2 (Case Management).
Tests Case creation, retrieval, cross-case BOLA protection, ID URL manipulation, query/body manipulation,
closed case modification protection, judicial context assignment, role escalation, and audit trail integrity.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.auth.service import AuthService
from src.cases.models import CaseStatus, CaseCreate, CaseUpdate, JudicialCaseContext
from src.audit.service import AuditService

client = TestClient(app)
auth_service = AuthService()


def get_token(username: str, password: str = "OfficerPass123!") -> str:
    if username == "officer1":
        pwd = "OfficerPass123!"
    elif username == "officer2":
        pwd = "OfficerPass456!"
    elif username == "boss1":
        pwd = "HigherAuthPass789!"
    elif username == "judge_specific":
        pwd = "JudgePass001!"
    elif username == "judge_high":
        pwd = "JudgePass002!"
    elif username == "judge_supreme":
        pwd = "JudgePass003!"
    else:
        pwd = password

    res = client.post("/api/v1/auth/login", json={"username": username, "password": pwd})
    assert res.status_code == 200, f"Login failed for {username}: {res.json()}"
    return res.json()["access_token"]


@pytest.fixture(autouse=True)
def ensure_c3_closed():
    import sqlite3
    db = sqlite3.connect("DATA/cases.db")
    db.execute("UPDATE cases SET status='CLOSED' WHERE case_id='CASE-2026-003'")
    db.commit()
    db.close()
    yield
    db = sqlite3.connect("DATA/cases.db")
    db.execute("UPDATE cases SET status='CLOSED' WHERE case_id='CASE-2026-003'")
    db.commit()
    db.close()


# ============================================================================
# 1. CASE CREATION TESTS (AUTHENTICATED VS UNAUTHENTICATED)
# ============================================================================

def test_authenticated_case_creation_success():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "case_name": "Operation Alpha Trident",
        "description": "Investigation into syndicated money transfers.",
        "assigned_investigators": ["USER-OFFICER-001"]
    }
    res = client.post("/api/v1/cases", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert "case_id" in data
    assert data["case_name"] == "Operation Alpha Trident"
    assert data["status"] == "DRAFT"
    assert data["created_by"] == "USER-OFFICER-001"


def test_unauthorized_case_creation_denied():
    payload = {"case_name": "Illegal Case", "description": "No Token"}
    res = client.post("/api/v1/cases", json=payload)
    assert res.status_code == 401


def test_judge_case_creation_denied():
    """BFLA Attack: Court Judge attempting to create a new investigation case directly."""
    token = get_token("judge_specific")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"case_name": "Judge Direct Creation", "description": "Illegal role action"}
    res = client.post("/api/v1/cases", json=payload, headers=headers)
    assert res.status_code == 403
    assert "cannot create cases" in res.json()["detail"]


# ============================================================================
# 2. CASE RETRIEVAL & CROSS-CASE BOLA ATTACK TESTS
# ============================================================================

def test_authorized_case_retrieval():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/cases/CASE-2026-001", headers=headers)
    assert res.status_code == 200
    assert res.json()["case_id"] == "CASE-2026-001"


def test_cross_case_url_id_manipulation_denied():
    """Adversarial BOLA Attack: Officer 1 manipulating case_id in URL to access Officer 2's case."""
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/cases/CASE-2026-002", headers=headers)
    assert res.status_code == 403
    assert "Officer not authorized for case" in res.json()["detail"]


def test_query_parameter_manipulation_defense():
    """Adversarial Attack: Attempting query parameter override like ?bypass=true or ?user_id=boss1."""
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/cases/CASE-2026-002?bypass=true&role=HIGHER_AUTHORITY", headers=headers)
    assert res.status_code == 403


def test_request_body_manipulation_defense():
    """Adversarial Attack: Modifying created_by or case_id in request payload during update."""
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    # Officer 1 attempts to change ownership or set case to CLOSED via request body
    payload = {
        "case_name": "Manipulated Name",
        "created_by": "USER-HACKER-999"
    }
    res = client.put("/api/v1/cases/CASE-2026-001", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    # created_by must remain untampered!
    assert data["created_by"] == "USER-OFFICER-001"


# ============================================================================
# 3. UNAUTHENTICATED & ROLE ESCALATION MODIFICATION TESTS
# ============================================================================

def test_unauthorized_case_update_denied():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"case_name": "Hacked Title"}
    # Officer 1 trying to update Officer 2's case
    res = client.put("/api/v1/cases/CASE-2026-002", json=payload, headers=headers)
    assert res.status_code == 403


def test_unauthorized_judicial_assignment_denied():
    """BFLA Attack: Officer 1 attempting to re-assign judicial context or judge."""
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "judicial_context": {
            "court_judge_id": "USER-JUDGE-003",
            "court_level": "SUPREME_COURT",
            "court_reference": "COURT-FORGED-999"
        }
    }
    res = client.put("/api/v1/cases/CASE-2026-001", json=payload, headers=headers)
    assert res.status_code == 403
    assert "cannot modify ownership or judicial assignment" in res.json()["detail"]


# ============================================================================
# 4. COURT LEVEL SCOPE VIOLATION TESTS
# ============================================================================

def test_court_scope_violation_denied():
    """Specific Court Judge attempting to inspect case belonging to another court."""
    token = get_token("judge_specific")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/cases/CASE-2026-002", headers=headers)
    assert res.status_code == 403
    assert "Specific Court judge not assigned to case" in res.json()["detail"]


def test_supreme_court_full_case_access():
    token = get_token("judge_supreme")
    headers = {"Authorization": f"Bearer {token}"}
    res1 = client.get("/api/v1/cases/CASE-2026-001", headers=headers)
    res2 = client.get("/api/v1/cases/CASE-2026-002", headers=headers)
    res3 = client.get("/api/v1/cases/CASE-2026-003", headers=headers)
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res3.status_code == 200


# ============================================================================
# 5. CLOSED CASE MODIFICATION & REOPENING TESTS
# ============================================================================

def test_closed_case_modification_denied():
    """Security Requirement: Closed cases cannot be modified."""
    token = get_token("boss1")
    headers = {"Authorization": f"Bearer {token}"}
    # CASE-2026-003 is CLOSED
    payload = {"description": "Attempting to alter closed case evidence description."}
    res = client.put("/api/v1/cases/CASE-2026-003", json=payload, headers=headers)
    assert res.status_code == 403
    assert "Modifications to closed cases are prohibited" in res.json()["detail"]


def test_officer_reopen_closed_case_denied():
    """BFLA Attack: Officer attempting to reopen a closed case."""
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.post("/api/v1/cases/CASE-2026-003/reopen", headers=headers)
    assert res.status_code == 403
    assert "cannot reopen a closed case" in res.json()["detail"]


def test_higher_authority_reopen_closed_case_allowed():
    token = get_token("boss1")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.post("/api/v1/cases/CASE-2026-003/reopen", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "ACTIVE"


# ============================================================================
# 6. AUDIT TRAIL GENERATION & INTEGRITY VERIFICATION
# ============================================================================

def test_case_actions_generate_tamper_evident_audit_trail():
    token = get_token("boss1")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Retrieve audit logs
    res = client.get("/api/v1/audit/logs", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["integrity_chain_valid"] is True
    assert data["total_events"] > 0
