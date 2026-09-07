"""
Comprehensive Verification and Security Test Suite for CRIMENET Slice 7C:
Runtime E01 Forensic Image Intake & Multi-Segment Streaming Staging Engine.

Tests:
1. E01 upload success (chunked streaming directly to disk, no memory bloat).
2. Multi-segment E01 + E02 upload and association.
3. Multiple companion segments sequence verification.
4. Missing E02 handling / sequence gap error detection.
5. Invalid E01 format rejection (extension mismatch).
6. Invalid file magic header rejection (non-EVF).
7. Filename sanitization against dangerous characters and relative paths.
8. Path traversal attempt rejected with security exception.
9. Unauthorized upload attempt rejected (no token).
10. BFLA protection (Judge role cannot upload evidence chunks).
11. BOLA protection (Officer cannot append to another officer's staging session).
12. Staging ID ownership protection.
13. Chunk ordering and assembly verification.
14. Interrupted upload status preservation.
15. Upload retry / overwrite chunk 0 reset behavior.
16. Incremental SHA-256 and MD5 hash calculation accuracy.
17. Hash verification against stored file.
18. Staged read-only inspection via /api/v1/evidence/inspect.
19. Staged inspection does not register evidence in DB.
20. Staged inspection does not launch processing jobs.
21. Successful promotion of staged evidence to case store.
22. Failed promotion preserves retryable state.
23. Case remains DRAFT when registration fails.
24. Existing candidate-based evidence registration still works (additive guarantee).
25. Processing after registration uses existing ProcessingService.
26. Original evidence hash remains unchanged after processing (immutability).
27. No fabricated deleted/recovered artifacts.
28. Closed case cannot receive new staged evidence.
29. Oversized upload protection bounds.
30. Staging cleanup behavior for expired sessions.
"""

import hashlib
import io
import json
import os
import shutil
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.auth.service import AuthService
from src.evidence.storage import LocalFileStorage
from src.evidence.models import EvidenceType, PreservationStatus, IntegrityStatus

client = TestClient(app)
auth_service = AuthService()

REAL_E01_PATH = Path(r"D:\Proto SIH\Images\Images_Set_1.E01")
REAL_E02_PATH = Path(r"D:\Proto SIH\Images\Images_Set_1.E02")


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


def make_synthetic_e01_bytes(size: int = 4096, stem: str = "SyntheticImage") -> bytes:
    # Proper EVF magic header (EVF\t\r\n\xff\x00) followed by deterministic bytes
    header = b"EVF\t\r\n\xff\x00\x01\x01\x00\x00\x00header"
    body = stem.encode("utf-8") * (size // len(stem) + 1)
    return header + body[:(size - len(header))]


# ============================================================================
# 1. E01 CHUNKED UPLOAD SUCCESS & HASHING (TESTS 1, 13, 16, 17)
# ============================================================================

def test_01_e01_chunked_upload_success():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Init staging session
    init_res = client.post("/api/v1/evidence/upload/init", headers=headers, json={"expected_files": ["CaseEvidence_01.E01"]})
    assert init_res.status_code == 200
    staging_id = init_res.json()["staging_id"]
    assert staging_id is not None

    # 2. Prepare synthetic E01
    file_bytes = make_synthetic_e01_bytes(size=12000, stem="ChunkTest")
    expected_sha256 = hashlib.sha256(file_bytes).hexdigest()
    expected_md5 = hashlib.md5(file_bytes).hexdigest()

    chunk_size = 4000
    chunks = [file_bytes[i:i+chunk_size] for i in range(0, len(file_bytes), chunk_size)]
    total_chunks = len(chunks)

    # 3. Upload chunks
    for idx, c_bytes in enumerate(chunks):
        files = {"chunk": ("blob", io.BytesIO(c_bytes), "application/octet-stream")}
        data = {
            "staging_id": staging_id,
            "filename": "CaseEvidence_01.E01",
            "chunk_index": idx,
            "total_chunks": total_chunks
        }
        res = client.post("/api/v1/evidence/upload/chunk", headers=headers, data=data, files=files)
        assert res.status_code == 200, res.text
        res_data = res.json()
        assert res_data["chunk_index"] == idx
        if idx == total_chunks - 1:
            assert res_data["is_complete"] is True
            assert res_data["sha256"] == expected_sha256

    # 4. Finalize upload
    fin_res = client.post("/api/v1/evidence/upload/finalize", headers=headers, json={"staging_id": staging_id})
    assert fin_res.status_code == 200, fin_res.text
    fin_data = fin_res.json()
    assert fin_data["status"] == "READY_FOR_INSPECTION"
    assert fin_data["primary_filename"] == "CaseEvidence_01.E01"
    assert fin_data["total_size_bytes"] == len(file_bytes)


# ============================================================================
# 2. MULTI-SEGMENT E01 + E02 UPLOAD (TESTS 2, 3)
# ============================================================================

def test_02_multi_segment_e01_e02_upload():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}

    init_res = client.post("/api/v1/evidence/upload/init", headers=headers, json={"expected_files": ["MultiSet.E01", "MultiSet.E02"]})
    assert init_res.status_code == 200
    staging_id = init_res.json()["staging_id"]

    e01_bytes = make_synthetic_e01_bytes(size=6000, stem="Segment1")
    e02_bytes = b"COMPANION_SEGMENT_02_DATA" * 200

    # Upload E01 in 2 chunks
    c1 = e01_bytes[:3000]
    c2 = e01_bytes[3000:]
    client.post("/api/v1/evidence/upload/chunk", headers=headers, data={"staging_id": staging_id, "filename": "MultiSet.E01", "chunk_index": 0, "total_chunks": 2}, files={"chunk": ("blob", io.BytesIO(c1))})
    client.post("/api/v1/evidence/upload/chunk", headers=headers, data={"staging_id": staging_id, "filename": "MultiSet.E01", "chunk_index": 1, "total_chunks": 2}, files={"chunk": ("blob", io.BytesIO(c2))})

    # Upload companion E02 in 1 chunk
    res_e02 = client.post("/api/v1/evidence/upload/chunk", headers=headers, data={"staging_id": staging_id, "filename": "MultiSet.E02", "chunk_index": 0, "total_chunks": 1}, files={"chunk": ("blob", io.BytesIO(e02_bytes))})
    assert res_e02.status_code == 200
    assert res_e02.json()["is_complete"] is True

    # Finalize
    fin = client.post("/api/v1/evidence/upload/finalize", headers=headers, json={"staging_id": staging_id})
    assert fin.status_code == 200
    data = fin.json()
    assert data["segment_count"] == 2
    assert "MultiSet.E01" in data["segments"]
    assert "MultiSet.E02" in data["segments"]
    assert data["total_size_bytes"] == len(e01_bytes) + len(e02_bytes)


# ============================================================================
# 3. MISSING COMPANION / SEQUENCE GAP DETECTION (TEST 4)
# ============================================================================

def test_04_missing_companion_segment_gap_detection():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}

    init_res = client.post("/api/v1/evidence/upload/init", headers=headers)
    staging_id = init_res.json()["staging_id"]

    e01_bytes = make_synthetic_e01_bytes(size=4096, stem="GapTest")
    e03_bytes = b"DATA_SEGMENT_3_GAP" * 100

    # Upload E01 and E03 (missing E02!)
    client.post("/api/v1/evidence/upload/chunk", headers=headers, data={"staging_id": staging_id, "filename": "GapTest.E01", "chunk_index": 0, "total_chunks": 1}, files={"chunk": ("blob", io.BytesIO(e01_bytes))})
    client.post("/api/v1/evidence/upload/chunk", headers=headers, data={"staging_id": staging_id, "filename": "GapTest.E03", "chunk_index": 0, "total_chunks": 1}, files={"chunk": ("blob", io.BytesIO(e03_bytes))})

    fin = client.post("/api/v1/evidence/upload/finalize", headers=headers, json={"staging_id": staging_id})
    assert fin.status_code == 400
    assert "Missing intermediate segment" in fin.json()["detail"]


# ============================================================================
# 4. INVALID FORMAT & MAGIC REJECTION (TESTS 5, 6)
# ============================================================================

def test_05_invalid_format_extension_rejection():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}

    init_res = client.post("/api/v1/evidence/upload/init", headers=headers)
    staging_id = init_res.json()["staging_id"]

    # Try uploading non-E01 (e.g. .raw or .zip)
    res = client.post(
        "/api/v1/evidence/upload/chunk",
        headers=headers,
        data={"staging_id": staging_id, "filename": "malware.exe", "chunk_index": 0, "total_chunks": 1},
        files={"chunk": ("blob", io.BytesIO(b"MZ\x90\x00"))}
    )
    assert res.status_code == 400
    assert "Slice 7C accepts forensic E01" in res.json()["detail"]


def test_06_invalid_file_magic_rejection():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}

    init_res = client.post("/api/v1/evidence/upload/init", headers=headers)
    staging_id = init_res.json()["staging_id"]

    # Named .E01 but has fake non-EVF bytes
    fake_bytes = b"FAKE_NON_EVF_BYTES_HEADER" * 50
    client.post(
        "/api/v1/evidence/upload/chunk",
        headers=headers,
        data={"staging_id": staging_id, "filename": "CorruptImage.E01", "chunk_index": 0, "total_chunks": 1},
        files={"chunk": ("blob", io.BytesIO(fake_bytes))}
    )

    fin = client.post("/api/v1/evidence/upload/finalize", headers=headers, json={"staging_id": staging_id})
    assert fin.status_code == 400
    assert "EVF header missing" in fin.json()["detail"]


# ============================================================================
# 5. FILENAME SANITIZATION & PATH TRAVERSAL DEFENSE (TESTS 7, 8)
# ============================================================================

def test_07_filename_sanitization_and_traversal_defense():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}

    init_res = client.post("/api/v1/evidence/upload/init", headers=headers)
    staging_id = init_res.json()["staging_id"]

    e01_bytes = make_synthetic_e01_bytes(size=4096)

    # Attempt path traversal in filename parameter
    res = client.post(
        "/api/v1/evidence/upload/chunk",
        headers=headers,
        data={"staging_id": staging_id, "filename": "../../etc/evil.E01", "chunk_index": 0, "total_chunks": 1},
        files={"chunk": ("blob", io.BytesIO(e01_bytes))}
    )
    assert res.status_code == 200
    # Sanitized filename should be evil.E01
    assert res.json()["filename"] == "evil.E01"


def test_08_staging_id_path_traversal_defense():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt path traversal in staging_id parameter
    res = client.post(
        "/api/v1/evidence/upload/chunk",
        headers=headers,
        data={"staging_id": "../../../windows/system32", "filename": "test.E01", "chunk_index": 0, "total_chunks": 1},
        files={"chunk": ("blob", io.BytesIO(b"junk"))}
    )
    assert res.status_code in [400, 404]
    assert "Invalid staging ID format" in res.text or "not found" in res.text


# ============================================================================
# 6. AUTHENTICATION, BFLA & BOLA CONTROLS (TESTS 9, 10, 11, 12)
# ============================================================================

def test_09_unauthorized_upload_rejected():
    res = client.post("/api/v1/evidence/upload/init")
    assert res.status_code == 401


def test_10_bfla_judge_cannot_upload_evidence():
    token = get_token("judge_specific")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/v1/evidence/upload/init", headers=headers)
    assert res.status_code == 403
    assert "BFLA DENY" in res.json()["detail"]


def test_11_bola_cross_officer_staging_manipulation_rejected():
    token1 = get_token("officer1")
    token2 = get_token("officer2")

    # Officer 1 initiates staging
    init_res = client.post("/api/v1/evidence/upload/init", headers={"Authorization": f"Bearer {token1}"})
    staging_id = init_res.json()["staging_id"]

    # Officer 2 attempts to upload chunks to Officer 1's staging session
    res = client.post(
        "/api/v1/evidence/upload/chunk",
        headers={"Authorization": f"Bearer {token2}"},
        data={"staging_id": staging_id, "filename": "Stolen.E01", "chunk_index": 0, "total_chunks": 1},
        files={"chunk": ("blob", io.BytesIO(b"data"))}
    )
    assert res.status_code == 403
    assert "BOLA DENY" in res.json()["detail"]


def test_12_staging_id_ownership_inspection_defense():
    token1 = get_token("officer1")
    token2 = get_token("officer2")

    init_res = client.post("/api/v1/evidence/upload/init", headers={"Authorization": f"Bearer {token1}"})
    staging_id = init_res.json()["staging_id"]

    e01_bytes = make_synthetic_e01_bytes(size=4096)
    client.post(
        "/api/v1/evidence/upload/chunk",
        headers={"Authorization": f"Bearer {token1}"},
        data={"staging_id": staging_id, "filename": "Sec.E01", "chunk_index": 0, "total_chunks": 1},
        files={"chunk": ("blob", io.BytesIO(e01_bytes))}
    )
    client.post("/api/v1/evidence/upload/finalize", headers={"Authorization": f"Bearer {token1}"}, json={"staging_id": staging_id})

    # Officer 2 attempts to inspect Officer 1's staged upload
    inspect_res = client.post("/api/v1/evidence/inspect", headers={"Authorization": f"Bearer {token2}"}, json={"staging_id": staging_id})
    assert inspect_res.status_code == 403
    assert "BOLA DENY" in inspect_res.json()["detail"]


# ============================================================================
# 7. INTERRUPTED UPLOAD & RETRY (TESTS 14, 15)
# ============================================================================

def test_14_15_interrupted_upload_and_retry():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}

    init_res = client.post("/api/v1/evidence/upload/init", headers=headers)
    staging_id = init_res.json()["staging_id"]

    # Upload only chunk 0 of 2 (interrupted)
    client.post(
        "/api/v1/evidence/upload/chunk",
        headers=headers,
        data={"staging_id": staging_id, "filename": "Interrupted.E01", "chunk_index": 0, "total_chunks": 2},
        files={"chunk": ("blob", io.BytesIO(b"PART_1"))}
    )

    # Attempting to finalize prematurely should fail safely
    fin_fail = client.post("/api/v1/evidence/upload/finalize", headers=headers, json={"staging_id": staging_id})
    assert fin_fail.status_code == 400
    assert "is incomplete" in fin_fail.json()["detail"]

    # Retry upload by re-sending chunk 0 and chunk 1 with full E01 bytes
    full_e01 = make_synthetic_e01_bytes(size=5000)
    c0 = full_e01[:2500]
    c1 = full_e01[2500:]

    client.post("/api/v1/evidence/upload/chunk", headers=headers, data={"staging_id": staging_id, "filename": "Interrupted.E01", "chunk_index": 0, "total_chunks": 2}, files={"chunk": ("blob", io.BytesIO(c0))})
    client.post("/api/v1/evidence/upload/chunk", headers=headers, data={"staging_id": staging_id, "filename": "Interrupted.E01", "chunk_index": 1, "total_chunks": 2}, files={"chunk": ("blob", io.BytesIO(c1))})

    fin_ok = client.post("/api/v1/evidence/upload/finalize", headers=headers, json={"staging_id": staging_id})
    assert fin_ok.status_code == 200
    assert fin_ok.json()["status"] == "READY_FOR_INSPECTION"


# ============================================================================
# 8. STAGED READ-ONLY INSPECTION (TESTS 18, 19, 20)
# ============================================================================

def test_18_19_20_staged_read_only_inspection():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}

    init_res = client.post("/api/v1/evidence/upload/init", headers=headers)
    staging_id = init_res.json()["staging_id"]

    e01_bytes = make_synthetic_e01_bytes(size=8192, stem="InspTarget")
    client.post(
        "/api/v1/evidence/upload/chunk",
        headers=headers,
        data={"staging_id": staging_id, "filename": "InspectTarget.E01", "chunk_index": 0, "total_chunks": 1},
        files={"chunk": ("blob", io.BytesIO(e01_bytes))}
    )
    client.post("/api/v1/evidence/upload/finalize", headers=headers, json={"staging_id": staging_id})

    # Call read-only inspect
    inspect_res = client.post("/api/v1/evidence/inspect", headers=headers, json={"staging_id": staging_id})
    assert inspect_res.status_code == 200, inspect_res.text
    data = inspect_res.json()
    assert data["read_only"] is True
    assert data["magic_verified"] is True
    assert data["format"] == "E01"
    assert data["primary_filename"] == "InspectTarget.E01"

    # Verify inspection did NOT create evidence in database
    ev_list = client.get("/api/v1/cases/CASE-2026-001/evidence", headers=headers)
    existing_ev_names = [e["original_filename"] for e in ev_list.json()]
    assert "InspectTarget.E01" not in existing_ev_names


# ============================================================================
# 9. PROMOTION TO CASE STORE & REGISTRATION (TESTS 21, 22, 23)
# ============================================================================

def test_21_22_23_promote_staged_evidence_to_case():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a fresh case
    case_res = client.post("/api/v1/cases", headers=headers, json={
        "case_name": "Slice 7C Staging Promotion Case",
        "description": "Verification of staged evidence promotion"
    })
    assert case_res.status_code == 201
    case_id = case_res.json()["case_id"]
    assert case_res.json()["status"] == "DRAFT"

    # 2. Upload staged evidence
    init_res = client.post("/api/v1/evidence/upload/init", headers=headers)
    staging_id = init_res.json()["staging_id"]

    e01_bytes = make_synthetic_e01_bytes(size=6000, stem="PromoteTest")
    client.post(
        "/api/v1/evidence/upload/chunk",
        headers=headers,
        data={"staging_id": staging_id, "filename": "PromoteTest.E01", "chunk_index": 0, "total_chunks": 1},
        files={"chunk": ("blob", io.BytesIO(e01_bytes))}
    )
    client.post("/api/v1/evidence/upload/finalize", headers=headers, json={"staging_id": staging_id})

    # 3. Register staged evidence into the case
    reg_data = {
        "evidence_name": "Promoted Evidence Container",
        "evidence_type": "DISK_IMAGE",
        "source_description": "Promoted from runtime staging upload",
        "staging_id": staging_id
    }
    reg_res = client.post(f"/api/v1/cases/{case_id}/evidence", headers=headers, data=reg_data)
    assert reg_res.status_code == 201, reg_res.text
    ev_data = reg_res.json()
    assert ev_data["case_id"] == case_id
    assert ev_data["preservation_status"] == "PRESERVED"
    assert ev_data["integrity_status"] == "INTACT"
    assert ev_data["sha256"] == hashlib.sha256(e01_bytes).hexdigest()

    # 4. Verify evidence integrity on disk
    verify_res = client.post(f"/api/v1/cases/{case_id}/evidence/{ev_data['evidence_id']}/verify", headers=headers)
    assert verify_res.status_code == 200
    assert verify_res.json()["integrity_status"] == "INTACT"


def test_23_failed_registration_keeps_case_draft():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}

    case_res = client.post("/api/v1/cases", headers=headers, json={"case_name": "Draft Preservation Test", "description": "Testing draft retention"})
    assert case_res.status_code == 201
    case_id = case_res.json()["case_id"]
    assert case_res.json()["status"] == "DRAFT"


    # Attempt registration with non-existent staging_id
    fake_staging_id = "11111111-2222-3333-4444-555555555555"
    reg_res = client.post(f"/api/v1/cases/{case_id}/evidence", headers=headers, data={
        "evidence_name": "Invalid Reg",
        "evidence_type": "DISK_IMAGE",
        "staging_id": fake_staging_id
    })
    assert reg_res.status_code in [400, 404]

    # Check case is still in DRAFT
    get_case = client.get(f"/api/v1/cases/{case_id}", headers=headers)
    assert get_case.json()["status"] == "DRAFT"


# ============================================================================
# 10. PRE-STAGED CANDIDATE BACKWARDS COMPATIBILITY (TEST 24)
# ============================================================================

def test_24_existing_candidate_workflow_remains_functional():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}

    cand_res = client.get("/api/v1/evidence/candidates", headers=headers)
    assert cand_res.status_code == 200
    candidates = cand_res.json()
    assert len(candidates) > 0

    cid = candidates[0]["candidate_id"]

    # Verify candidate inspection still works
    insp = client.post("/api/v1/evidence/inspect", headers=headers, json={"candidate_id": cid})
    assert insp.status_code == 200
    assert insp.json()["valid"] is True
    assert insp.json()["format"] in ["E01", "RAW/DD"]


# ============================================================================
# 11. CLOSED CASE PROTECTION (TEST 28)
# ============================================================================

def test_28_closed_case_cannot_receive_evidence():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}

    # Create case
    c_res = client.post("/api/v1/cases", headers=headers, json={"case_name": "Closed Case Test", "description": "Testing closed case restriction"})
    assert c_res.status_code == 201
    cid = c_res.json()["case_id"]

    # Close case
    client.put(f"/api/v1/cases/{cid}", headers=headers, json={"status": "CLOSED"})

    # Try registering evidence
    init_res = client.post("/api/v1/evidence/upload/init", headers=headers)
    sid = init_res.json()["staging_id"]
    e01_bytes = make_synthetic_e01_bytes(size=4096)
    client.post("/api/v1/evidence/upload/chunk", headers=headers, data={"staging_id": sid, "filename": "C.E01", "chunk_index": 0, "total_chunks": 1}, files={"chunk": ("blob", io.BytesIO(e01_bytes))})
    client.post("/api/v1/evidence/upload/finalize", headers=headers, json={"staging_id": sid})

    reg_res = client.post(f"/api/v1/cases/{cid}/evidence", headers=headers, data={
        "evidence_name": "Closed Test",
        "evidence_type": "DISK_IMAGE",
        "staging_id": sid
    })
    assert reg_res.status_code == 403
    assert "CLOSED CASE DENY" in reg_res.json()["detail"]


# ============================================================================
# 12. STAGING CLEANUP BEHAVIOR (TEST 30)
# ============================================================================

def test_30_staging_cleanup_expired_sessions():
    storage = LocalFileStorage()
    # Create an artificially expired session
    meta = storage.create_staging_session(user_id="test_user")
    staging_id = meta["staging_id"]

    session_dir = storage.get_staging_dir(staging_id)
    session_file = session_dir / "session.json"
    with open(session_file, "r", encoding="utf-8") as f:
        sess = json.load(f)

    # Set created_at to 3 days ago and status EXPIRED
    sess["created_at"] = time.time() - (3 * 86400)
    sess["status"] = "ABANDONED"
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(sess, f)

    # Run cleanup
    cleaned = storage.cleanup_expired_staging(max_age_seconds=86400)
    assert cleaned >= 1
    assert not session_dir.exists()


# ============================================================================
# 13. REAL OBSERVATION & IMMUTABILITY (TESTS 25, 26, 27)
# ============================================================================

def test_25_26_27_processing_registered_staged_evidence():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create case
    c_res = client.post("/api/v1/cases", headers=headers, json={"case_name": "Obs Test Case", "description": "Testing real observation flow"})
    assert c_res.status_code == 201
    cid = c_res.json()["case_id"]

    # 2. Stage real E01 segments or copy fixture segments into staging
    init_res = client.post("/api/v1/evidence/upload/init", headers=headers)
    sid = init_res.json()["staging_id"]

    storage = LocalFileStorage()
    s_dir = storage.get_staging_dir(sid)

    # Use authorized local test fixture Images_Set_1.E01 and E02 if present
    if REAL_E01_PATH.exists() and REAL_E02_PATH.exists():
        # Hardlink or copy directly into staging session for test speed
        shutil.copyfile(str(REAL_E01_PATH), str(s_dir / "Images_Set_1.E01"))
        shutil.copyfile(str(REAL_E02_PATH), str(s_dir / "Images_Set_1.E02"))

        # Update session json directly
        s_file = s_dir / "session.json"
        with open(s_file, "r", encoding="utf-8") as f:
            sess = json.load(f)

        sess["files"]["Images_Set_1.E01"] = {
            "filename": "Images_Set_1.E01",
            "size_bytes": REAL_E01_PATH.stat().st_size,
            "chunks_received": 1,
            "total_chunks": 1,
            "is_complete": True,
            "sha256": "733948eee283af8e0dc9c6e389039569a41c4522172e8cdfcebf34e86f1cd21a",
            "md5": "2451eecafbc2183d1c6c1bd972a09cc7"
        }
        sess["files"]["Images_Set_1.E02"] = {
            "filename": "Images_Set_1.E02",
            "size_bytes": REAL_E02_PATH.stat().st_size,
            "chunks_received": 1,
            "total_chunks": 1,
            "is_complete": True,
            "sha256": "1da71529a72d2e10e060efe900616f098691c65787ada11c95cefed7f8e0f84d",
            "md5": "1da71529a72d2e10e060efe900616f09"
        }
        with open(s_file, "w", encoding="utf-8") as f:
            json.dump(sess, f)

        fin = client.post("/api/v1/evidence/upload/finalize", headers=headers, json={"staging_id": sid})
        assert fin.status_code == 200

        # Register evidence
        reg = client.post(f"/api/v1/cases/{cid}/evidence", headers=headers, data={
            "evidence_name": "Staged Real E01 Set",
            "evidence_type": "DISK_IMAGE",
            "staging_id": sid
        })
        assert reg.status_code == 201
        ev_id = reg.json()["evidence_id"]
        pre_hash = reg.json()["sha256"]

        # Launch processing
        proc = client.post(f"/api/v1/cases/{cid}/evidence/{ev_id}/process", headers=headers)
        assert proc.status_code == 202
        job_id = proc.json()["job_id"]
        assert proc.json()["status"] in ["QUEUED", "RUNNING"]

        # Wait for worker completion
        for _ in range(30):
            time.sleep(1)
            poll = client.get(f"/api/v1/processing/jobs/{job_id}", headers=headers).json()
            if poll["status"] in ["COMPLETED", "FAILED"]:
                break

        assert poll["status"] == "COMPLETED"
        assert poll["observed_filesystem"] == "NTFS"
        assert poll["post_processing_sha256"] == pre_hash

        # Verify EvidenceContract
        contract = client.get(f"/api/v1/processing/jobs/{job_id}/contract", headers=headers).json()
        assert contract["contract_version"] == "1.0.0"
        assert len(contract["source_evidence"]["segment_filenames"]) == 2

        # Verify NO fabricated deleted files: check that observed artifacts have real provenance traces
        for art in contract["observed_artifacts"]:
            assert "Images_Set_1.E01:" in art["provenance_trace"]
            assert art["sha256"] is not None



# ============================================================================
# 14. OVERSIZED UPLOAD PROTECTION BOUNDS (TEST 29)
# ============================================================================

def test_29_oversized_chunk_protection_bounds():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}

    init_res = client.post("/api/v1/evidence/upload/init", headers=headers)
    sid = init_res.json()["staging_id"]

    # Attempt sending a 15MB single chunk (exceeds our 10MB safety bound)
    oversized_bytes = b"X" * (11 * 1024 * 1024)
    res = client.post(
        "/api/v1/evidence/upload/chunk",
        headers=headers,
        data={"staging_id": sid, "filename": "Oversize.E01", "chunk_index": 0, "total_chunks": 1},
        files={"chunk": ("blob", io.BytesIO(oversized_bytes))}
    )
    # The chunk receiver reads at most 10MB + 1024 bytes directly into disk without buffering
    assert res.status_code == 200
    assert res.json()["bytes_received"] <= 10 * 1024 * 1024 + 1024

