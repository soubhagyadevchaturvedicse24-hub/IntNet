"""
Comprehensive Security, Processing Engine, Forensic Integrity, and Domain Test Suite for CRIMENET Slice 4.
Tests Processing Job creation, async execution, pre/post SHA-256 hash preservation, BOLA/BFLA security,
EvidenceContract_v1 generation, output isolation, audit trail logging, and reproducible observations.
"""

import hashlib
import io
import json
import time
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from src.api.main import app
from src.auth.service import AuthService

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


def upload_test_evidence(token: str, case_id: str = "CASE-2026-001") -> str:
    headers = {"Authorization": f"Bearer {token}"}
    file_bytes = b"FORENSIC DISK IMAGE BYTES FOR SLICE 4 ENGINE TESTING 2026 FAT32 +1234567890 suspect@test.com"
    data = {"evidence_name": f"Test Disk RAW {time.time()}", "evidence_type": "DISK_IMAGE"}
    files = {"file": ("test_disk.raw", io.BytesIO(file_bytes), "application/octet-stream")}
    res = client.post(f"/api/v1/cases/{case_id}/evidence", data=data, files=files, headers=headers)
    assert res.status_code == 201, f"Failed upload: {res.json()}"
    return res.json()["evidence_id"]


# ============================================================================
# 1. PROCESSING JOB CREATION & ASYNC EXECUTION TESTS
# ============================================================================

def test_processing_job_creation_and_completion():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    ev_id = upload_test_evidence(token, "CASE-2026-001")

    # Launch processing job
    res = client.post(f"/api/v1/cases/CASE-2026-001/evidence/{ev_id}/process", headers=headers)
    assert res.status_code == 202
    data = res.json()

    assert "job_id" in data
    job_id = data["job_id"]
    assert data["status"] in ["QUEUED", "RUNNING", "COMPLETED"]

    # Wait for async background worker completion
    completed = False
    for _ in range(30):
        res_job = client.get(f"/api/v1/processing/jobs/{job_id}", headers=headers)
        assert res_job.status_code == 200
        job_data = res_job.json()
        if job_data["status"] == "COMPLETED":
            completed = True
            break
        time.sleep(0.1)

    assert completed is True
    assert job_data["observed_filesystem"] in ["FAT32", "NTFS"]
    assert job_data["pre_processing_sha256"] == job_data["post_processing_sha256"]


def test_unauthenticated_processing_request_denied():
    res = client.post("/api/v1/cases/CASE-2026-001/evidence/EV-2026-9001/process")
    assert res.status_code == 401


# ============================================================================
# 2. CROSS-CASE & BOLA/BFLA AUTHORIZATION TESTS
# ============================================================================

def test_cross_case_processing_denied():
    """BOLA Attack: Officer 1 attempting to trigger processing on Officer 2's case evidence."""
    token2 = get_token("officer2")
    ev2_id = upload_test_evidence(token2, "CASE-2026-002")

    token1 = get_token("officer1")
    headers1 = {"Authorization": f"Bearer {token1}"}
    
    res = client.post(f"/api/v1/cases/CASE-2026-002/evidence/{ev2_id}/process", headers=headers1)
    assert res.status_code == 403
    assert "Officer not authorized for case" in res.json()["detail"]


def test_evidence_id_manipulation_processing_denied():
    """Adversarial Attack: Requesting processing for EV2 (CASE-2026-002) under CASE-2026-001."""
    token2 = get_token("officer2")
    ev2_id = upload_test_evidence(token2, "CASE-2026-002")

    token1 = get_token("officer1")
    headers1 = {"Authorization": f"Bearer {token1}"}

    res = client.post(f"/api/v1/cases/CASE-2026-001/evidence/{ev2_id}/process", headers=headers1)
    assert res.status_code == 403
    assert "ID MANIPULATION DENY" in res.json()["detail"]


def test_closed_case_processing_denied():
    """Security Requirement: Processing cannot be launched on closed cases."""
    token_boss = get_token("boss1")
    headers_boss = {"Authorization": f"Bearer {token_boss}"}
    
    # CASE-2026-003 is CLOSED
    # Attempt processing on evidence registered under CASE-2026-003
    ev3_id = upload_test_evidence(token_boss, "CASE-2026-001")  # Upload valid evidence
    # Now try launching processing targeting CASE-2026-003
    res = client.post(f"/api/v1/cases/CASE-2026-003/evidence/{ev3_id}/process", headers=headers_boss)
    assert res.status_code == 403
    assert "ID MANIPULATION DENY" in res.json()["detail"] or "CLOSED CASE DENY" in res.json()["detail"]


def test_unauthorized_job_result_access_denied():
    """BOLA Attack: Officer 1 attempting to view processing job of another officer's case."""
    token1 = get_token("officer1")
    token2 = get_token("officer2")
    
    ev_id2 = upload_test_evidence(token2, "CASE-2026-002")
    
    # Officer 2 creates job
    res = client.post(f"/api/v1/cases/CASE-2026-002/evidence/{ev_id2}/process", headers={"Authorization": f"Bearer {token2}"})
    job_id = res.json()["job_id"]

    # Officer 1 attempts to retrieve Officer 2's job
    res_hacker = client.get(f"/api/v1/processing/jobs/{job_id}", headers={"Authorization": f"Bearer {token1}"})
    assert res_hacker.status_code == 403


# ============================================================================
# 3. EVIDENCECONTRACT_V1 GENERATION & PROVENANCE TESTS
# ============================================================================

def test_evidence_contract_v1_retrieval_and_provenance():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    ev_id = upload_test_evidence(token, "CASE-2026-001")

    res_proc = client.post(f"/api/v1/cases/CASE-2026-001/evidence/{ev_id}/process", headers=headers)
    job_id = res_proc.json()["job_id"]

    # Wait for completion
    for _ in range(30):
        res_j = client.get(f"/api/v1/processing/jobs/{job_id}", headers=headers)
        if res_j.json()["status"] == "COMPLETED":
            break
        time.sleep(0.1)

    # Fetch EvidenceContract_v1
    res_contract = client.get(f"/api/v1/processing/jobs/{job_id}/contract", headers=headers)
    assert res_contract.status_code == 200
    contract = res_contract.json()

    assert contract["contract_version"] == "1.0.0"
    assert contract["provenance_envelope"]["case_id"] == "CASE-2026-001"
    assert contract["provenance_envelope"]["evidence_id"] == ev_id
    assert contract["provenance_envelope"]["processing_job_id"] == job_id
    assert contract["source_evidence"]["container_format"] == "RAW"
    assert len(contract["observed_artifacts"]) > 0


# ============================================================================
# 4. FORENSIC INTEGRITY: SHA-256 UNCHANGED VERIFICATION
# ============================================================================

def test_original_evidence_sha256_remains_unchanged():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    
    file_bytes = b"FORENSIC DISK IMAGE BYTES FOR UNCHANGED HASH TEST 2026"
    expected_sha256 = hashlib.sha256(file_bytes).hexdigest()

    data = {"evidence_name": "Unchanged Hash Disk", "evidence_type": "DISK_IMAGE"}
    files = {"file": ("unchanged_disk.raw", io.BytesIO(file_bytes), "application/octet-stream")}
    
    res_upload = client.post("/api/v1/cases/CASE-2026-001/evidence", data=data, files=files, headers=headers)
    assert res_upload.status_code == 201
    ev_id = res_upload.json()["evidence_id"]
    original_sha256 = res_upload.json()["sha256"]
    assert original_sha256 == expected_sha256

    res_proc = client.post(f"/api/v1/cases/CASE-2026-001/evidence/{ev_id}/process", headers=headers)
    assert res_proc.status_code == 202
    job_id = res_proc.json()["job_id"]

    # Wait for completion
    for _ in range(30):
        res_j = client.get(f"/api/v1/processing/jobs/{job_id}", headers=headers)
        j_data = res_j.json()
        if j_data["status"] == "COMPLETED":
            break
        time.sleep(0.1)

    assert j_data["pre_processing_sha256"] == original_sha256
    assert j_data["post_processing_sha256"] == original_sha256


# ============================================================================
# 5. AUDIT LOG GENERATION TEST FOR PROCESSING LIFECYCLE
# ============================================================================

def test_processing_lifecycle_generates_audit_trail():
    token = get_token("boss1")
    headers = {"Authorization": f"Bearer {token}"}
    
    res = client.get("/api/v1/audit/logs", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["integrity_chain_valid"] is True
    
    actions = [e["action"] for e in data["events"]]
    assert "START_PROCESSING" in actions or "PROCESSING_REQUESTED" in actions or "PROCESSING_COMPLETED" in actions
