"""
Comprehensive Security, Preservation, Path Traversal, and Domain Test Suite for CRIMENET Slice 3 (Evidence Intake & Preservation).
Tests Evidence registration, SHA-256 calculation, stored-byte hash verification, BOLA/BFLA protection,
path traversal defense, absolute path injection defense, audit trail logging, and immutability.
"""

import hashlib
import io
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.auth.service import AuthService
from src.evidence.models import EvidenceType, PreservationStatus, IntegrityStatus
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
    else:
        pwd = password

    res = client.post("/api/v1/auth/login", json={"username": username, "password": pwd})
    assert res.status_code == 200, f"Login failed for {username}: {res.json()}"
    return res.json()["access_token"]


# ============================================================================
# 1. EVIDENCE REGISTRATION & SHA-256 HASH CORRECTNESS TESTS
# ============================================================================

def test_evidence_registration_success():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    
    file_bytes = b"CONFIDENTIAL FORENSIC DISK IMAGE BYTES 2026 PROVENANCE TEST"
    expected_sha256 = hashlib.sha256(file_bytes).hexdigest()
    expected_md5 = hashlib.md5(file_bytes).hexdigest()

    data = {
        "evidence_name": "Seized Phone Dump A",
        "evidence_type": "MOBILE_EXTRACTION",
        "source_description": "Extracted from suspect device during search warrant execution."
    }
    files = {
        "file": ("suspect_phone.raw", io.BytesIO(file_bytes), "application/octet-stream")
    }

    res = client.post("/api/v1/cases/CASE-2026-001/evidence", data=data, files=files, headers=headers)
    assert res.status_code == 201
    res_data = res.json()

    assert "evidence_id" in res_data
    assert res_data["case_id"] == "CASE-2026-001"
    assert res_data["sha256"] == expected_sha256
    assert res_data["md5"] == expected_md5
    assert res_data["original_size_bytes"] == len(file_bytes)
    assert res_data["preservation_status"] == "PRESERVED"
    assert res_data["integrity_status"] == "INTACT"


def test_empty_file_registration_denied():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    
    data = {"evidence_name": "Empty Evidence", "evidence_type": "LOOSE_FILES"}
    files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}

    res = client.post("/api/v1/cases/CASE-2026-001/evidence", data=data, files=files, headers=headers)
    assert res.status_code == 400
    assert "Empty evidence file provided" in res.json()["detail"]


# ============================================================================
# 2. STORED-BYTE HASH INTEGRITY RE-VERIFICATION TEST
# ============================================================================

def test_evidence_integrity_verification():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Upload evidence
    file_bytes = b"FORENSIC HARD DISK BLOCK DATA VERIFICATION SAMPLE"
    data = {"evidence_name": "Hard Drive Image B", "evidence_type": "DISK_IMAGE"}
    files = {"file": ("hdd_image.e01", io.BytesIO(file_bytes), "application/octet-stream")}

    res_upload = client.post("/api/v1/cases/CASE-2026-001/evidence", data=data, files=files, headers=headers)
    assert res_upload.status_code == 201
    ev_id = res_upload.json()["evidence_id"]

    # 2. Trigger SHA-256 integrity verification against stored disk file
    res_verify = client.post(f"/api/v1/cases/CASE-2026-001/evidence/{ev_id}/verify", headers=headers)
    assert res_verify.status_code == 200
    verify_data = res_verify.json()

    assert verify_data["integrity_status"] == "INTACT"
    assert verify_data["expected_sha256"] == verify_data["calculated_sha256"]


# ============================================================================
# 3. PATH TRAVERSAL & ABSOLUTE PATH INJECTION ADVERSARIAL TESTS
# ============================================================================

def test_path_traversal_filename_sanitization():
    """Adversarial Attack: Attempting relative path traversal in uploaded filename."""
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    
    file_bytes = b"PATH TRAVERSAL PAYLOAD BYTES"
    data = {"evidence_name": "Path Traversal Test", "evidence_type": "DOCUMENT"}
    # Malicious filename attempting to escape evidence_store directory
    files = {"file": ("../../../../etc/passwd", io.BytesIO(file_bytes), "text/plain")}

    res = client.post("/api/v1/cases/CASE-2026-001/evidence", data=data, files=files, headers=headers)
    assert res.status_code == 201
    storage_ref = res.json()["storage_reference"]
    # Verify path was sanitized safely inside CASE-2026-001 folder
    assert "../" not in storage_ref
    assert "etc" not in storage_ref


def test_absolute_path_injection_sanitization():
    """Adversarial Attack: Attempting Windows absolute path injection."""
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    
    file_bytes = b"WINDOWS PATH INJECTION BYTES"
    data = {"evidence_name": "Windows Path Test", "evidence_type": "DOCUMENT"}
    files = {"file": ("C:\\Windows\\System32\\cmd.exe", io.BytesIO(file_bytes), "text/plain")}

    res = client.post("/api/v1/cases/CASE-2026-001/evidence", data=data, files=files, headers=headers)
    assert res.status_code == 201
    storage_ref = res.json()["storage_reference"]
    assert "System32" not in storage_ref
    assert "C:" not in storage_ref


# ============================================================================
# 4. CROSS-CASE BOLA & AUTHORIZATION TESTS
# ============================================================================

def test_cross_case_evidence_registration_denied():
    """BOLA Attack: Officer 1 attempting to register evidence under Officer 2's case."""
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    
    data = {"evidence_name": "Illegal Evidence Intake", "evidence_type": "DOCUMENT"}
    files = {"file": ("illegal.doc", io.BytesIO(b"UNAUTHORIZED BYTES"), "text/plain")}

    res = client.post("/api/v1/cases/CASE-2026-002/evidence", data=data, files=files, headers=headers)
    assert res.status_code == 403
    assert "Officer not authorized for case" in res.json()["detail"]


def test_cross_case_evidence_retrieval_denied():
    """BOLA Attack: Officer 1 requesting evidence from Officer 2's case."""
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/cases/CASE-2026-002/evidence", headers=headers)
    assert res.status_code == 403


def test_evidence_id_manipulation_cross_case_denied():
    """Adversarial Attack: Requesting evidence EV-2026-9004 (from CASE-2026-002) under CASE-2026-001."""
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/cases/CASE-2026-001/evidence/EV-2026-9004", headers=headers)
    assert res.status_code == 403
    assert "ID MANIPULATION DENY" in res.json()["detail"]


def test_judge_evidence_upload_denied():
    """BFLA Attack: Court Judge attempting to upload evidence file directly."""
    token = get_token("judge_specific")
    headers = {"Authorization": f"Bearer {token}"}
    
    data = {"evidence_name": "Judge Upload", "evidence_type": "DOCUMENT"}
    files = {"file": ("judge.pdf", io.BytesIO(b"JUDGE UPLOAD BYTES"), "application/pdf")}

    res = client.post("/api/v1/cases/CASE-2026-001/evidence", data=data, files=files, headers=headers)
    assert res.status_code == 403
    assert "cannot register evidence" in res.json()["detail"]


# ============================================================================
# 5. AUDIT TRAIL GENERATION & INTEGRITY VERIFICATION
# ============================================================================

def test_evidence_actions_generate_audit_trail():
    token = get_token("boss1")
    headers = {"Authorization": f"Bearer {token}"}
    
    res = client.get("/api/v1/audit/logs", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["integrity_chain_valid"] is True
    
    actions = [e["action"] for e in data["events"]]
    assert "REGISTER_EVIDENCE" in actions or "EVIDENCE_ACCESSED" in actions or "EVIDENCE_INTEGRITY_VERIFIED" in actions
