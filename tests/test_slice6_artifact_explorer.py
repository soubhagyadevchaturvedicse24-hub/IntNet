"""
Comprehensive Security, Artifact Categorization, Provenance, BOLA Defense,
Path Traversal Shield, and Domain Test Suite for CRIMENET Slice 6.
Tests Layer 1 File taxonomy, allocation/recovery status precision, Case-scoped Evidence Explorer APIs,
idempotency, path traversal denial, original evidence hash preservation, and full regression.
"""

import io
import time
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from src.api.main import app
from src.auth.service import AuthService
from src.artifacts.models import (
    Artifact,
    ArtifactCategory,
    AllocationStatus,
    RecoveryStatus,
    ViewerType,
    ProvenanceEnvelope
)
from src.artifacts.service import ArtifactService

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
    file_bytes = b"SLICE 6 EVIDENCE TEST DISK RAW FAT32 +1987654321 evidence@test.com"
    data = {"evidence_name": f"Slice6 RAW Image {time.time()}", "evidence_type": "DISK_IMAGE"}
    files = {"file": ("test_slice6_disk.raw", io.BytesIO(file_bytes), "application/octet-stream")}
    res = client.post(f"/api/v1/cases/{case_id}/evidence", data=data, files=files, headers=headers)
    assert res.status_code == 201, f"Failed upload: {res.json()}"
    return res.json()["evidence_id"]


def run_processing_job(token: str, case_id: str, evidence_id: str) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    res = client.post(f"/api/v1/cases/{case_id}/evidence/{evidence_id}/process", headers=headers)
    assert res.status_code == 202
    job_id = res.json()["job_id"]

    for _ in range(30):
        res_j = client.get(f"/api/v1/processing/jobs/{job_id}", headers=headers)
        if res_j.json()["status"] == "COMPLETED":
            break
        time.sleep(0.1)

    return job_id


# ============================================================================
# 1. LAYER 1 ARTIFACT CATEGORIZATION & CLASSIFICATION TESTS
# ============================================================================

def test_layer1_artifact_categorization_and_mime_mapping():
    """Validates Layer 1 file taxonomy categorization without creating Layer 2 entities."""
    srv = ArtifactService()

    cat, mime, ext, viewer = srv.classify_artifact("partition.hdr", "PARTITION_TABLE")
    assert cat == ArtifactCategory.PARTITION_TABLE
    assert viewer == ViewerType.HEX

    cat, mime, ext, viewer = srv.classify_artifact("suspect_chats.db", "DATABASE")
    assert cat == ArtifactCategory.DATABASE
    assert mime == "application/x-sqlite3"
    assert viewer == ViewerType.DATABASE

    cat, mime, ext, viewer = srv.classify_artifact("deleted_photo.jpg", "IMAGE")
    assert cat == ArtifactCategory.IMAGE
    assert mime == "image/jpeg"
    assert viewer == ViewerType.IMAGE

    cat, mime, ext, viewer = srv.classify_artifact("report.pdf", "DOCUMENT")
    assert cat == ArtifactCategory.DOCUMENT
    assert mime == "application/pdf"
    assert viewer == ViewerType.PDF

    cat, mime, ext, viewer = srv.classify_artifact("call_log.csv", "CDR")
    assert cat == ArtifactCategory.CDR
    assert mime == "text/csv"
    assert viewer == ViewerType.SPREADSHEET


def test_artifact_ingestion_from_evidence_contract():
    """Verifies artifact ingestion from EvidenceContract_v1 into Artifact domain repository."""
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    ev_id = upload_test_evidence(token, "CASE-2026-001")
    job_id = run_processing_job(token, "CASE-2026-001", ev_id)

    res = client.get(f"/api/v1/cases/CASE-2026-001/artifacts?evidence_id={ev_id}", headers=headers)
    assert res.status_code == 200
    artifacts = res.json()

    assert len(artifacts) > 0
    art = artifacts[0]
    assert art["case_id"] == "CASE-2026-001"
    assert art["evidence_id"] == ev_id
    assert art["processing_job_id"] == job_id
    assert art["provenance_chain"]["engine_name"] == "CRIMENET_RAW_OBSERVATION_ENGINE"


def test_idempotent_duplicate_artifact_ingestion():
    """Guarantees that re-ingesting the exact same contract payload does not duplicate artifact entries."""
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    ev_id = upload_test_evidence(token, "CASE-2026-001")
    job_id = run_processing_job(token, "CASE-2026-001", ev_id)

    res1 = client.get(f"/api/v1/cases/CASE-2026-001/artifacts?processing_job_id={job_id}", headers=headers)
    count1 = len(res1.json())

    # Fetch contract payload
    res_contract = client.get(f"/api/v1/processing/jobs/{job_id}/contract", headers=headers)
    contract = res_contract.json()

    # Re-trigger ingestion manually
    srv = ArtifactService()

    class DummyJob:
        def __init__(self, c_id: str, e_id: str, j_id: str):
            self.case_id = c_id
            self.evidence_id = e_id
            self.job_id = j_id
            self.engine_name = "CRIMENET_RAW_OBSERVATION_ENGINE"
            self.engine_version = "1.0.0"

    srv.ingest_contract_artifacts(contract, DummyJob("CASE-2026-001", ev_id, job_id))

    res2 = client.get(f"/api/v1/cases/CASE-2026-001/artifacts?processing_job_id={job_id}", headers=headers)
    count2 = len(res2.json())

    assert count1 == count2, "Idempotency failure: Repeated ingestion created duplicate artifacts!"


# ============================================================================
# 2. EVIDENCE EXPLORER API & MULTI-CRITERIA FILTERING TESTS
# ============================================================================

def test_evidence_explorer_multi_criteria_filtering():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    ev_id = upload_test_evidence(token, "CASE-2026-001")
    job_id = run_processing_job(token, "CASE-2026-001", ev_id)

    # Filter by category
    res = client.get(f"/api/v1/cases/CASE-2026-001/artifacts?category=PARTITION_TABLE", headers=headers)
    assert res.status_code == 200
    for a in res.json():
        assert a["category"] == "PARTITION_TABLE"

    # Filter by evidence_id
    res_ev = client.get(f"/api/v1/cases/CASE-2026-001/artifacts?evidence_id={ev_id}", headers=headers)
    assert res_ev.status_code == 200
    assert len(res_ev.json()) > 0

    # Filter by non-existent category returns empty list
    res_empty = client.get(f"/api/v1/cases/CASE-2026-001/artifacts?category=EMAIL", headers=headers)
    assert res_empty.status_code == 200
    assert len(res_empty.json()) == 0


def test_artifact_details_retrieval_and_viewer_recommendation():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    ev_id = upload_test_evidence(token, "CASE-2026-001")
    job_id = run_processing_job(token, "CASE-2026-001", ev_id)

    res_list = client.get(f"/api/v1/cases/CASE-2026-001/artifacts", headers=headers)
    art_id = res_list.json()[0]["artifact_id"]

    res_single = client.get(f"/api/v1/cases/CASE-2026-001/artifacts/{art_id}", headers=headers)
    assert res_single.status_code == 200
    data = res_single.json()

    assert data["artifact_id"] == art_id
    assert data["case_id"] == "CASE-2026-001"
    assert "recommended_viewer" in data
    assert data["allocation_status"] in ["ALLOCATED", "UNALLOCATED", "DELETED", "UNKNOWN"]
    assert data["recovery_status"] in ["NONE", "RECOVERED", "CARVED", "PARTIAL", "UNKNOWN"]


# ============================================================================
# 3. SECURITY & BOLA / PRIVILEGE ESCALATION TESTS
# ============================================================================

def test_unauthenticated_artifact_access_denied():
    res = client.get("/api/v1/cases/CASE-2026-001/artifacts")
    assert res.status_code == 401


def test_cross_case_artifact_access_denied():
    """BOLA Attack: Officer 1 attempting to read artifacts from Officer 2's case (CASE-2026-002)."""
    token2 = get_token("officer2")
    ev2_id = upload_test_evidence(token2, "CASE-2026-002")
    job2_id = run_processing_job(token2, "CASE-2026-002", ev2_id)

    token1 = get_token("officer1")
    headers1 = {"Authorization": f"Bearer {token1}"}

    res = client.get("/api/v1/cases/CASE-2026-002/artifacts", headers=headers1)
    assert res.status_code == 403
    assert "Officer not authorized for case" in res.json()["detail"]


def test_artifact_id_manipulation_cross_case_denied():
    """Adversarial Attack: Requesting Officer 2's artifact under Officer 1's case_id URL."""
    token2 = get_token("officer2")
    ev2_id = upload_test_evidence(token2, "CASE-2026-002")
    job2_id = run_processing_job(token2, "CASE-2026-002", ev2_id)

    res2_list = client.get("/api/v1/cases/CASE-2026-002/artifacts", headers={"Authorization": f"Bearer {token2}"})
    art2_id = res2_list.json()[0]["artifact_id"]

    token1 = get_token("officer1")
    headers1 = {"Authorization": f"Bearer {token1}"}

    res_hacker = client.get(f"/api/v1/cases/CASE-2026-001/artifacts/{art2_id}", headers=headers1)
    assert res_hacker.status_code == 403
    assert "ID MANIPULATION DENY" in res_hacker.json()["detail"] or "Officer not authorized" in res_hacker.json()["detail"]


# ============================================================================
# 4. PATH TRAVERSAL SHIELD & SECURE CONTENT ACCESS TESTS
# ============================================================================

def test_safe_content_access():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    ev_id = upload_test_evidence(token, "CASE-2026-001")
    job_id = run_processing_job(token, "CASE-2026-001", ev_id)

    res_list = client.get(f"/api/v1/cases/CASE-2026-001/artifacts", headers=headers)
    art_id = res_list.json()[0]["artifact_id"]

    res_content = client.get(f"/api/v1/cases/CASE-2026-001/artifacts/{art_id}/content", headers=headers)
    assert res_content.status_code == 200
    assert len(res_content.content) > 0


def test_path_traversal_attack_rejection():
    """Security Requirement: Verify that path traversal parameters are strictly rejected."""
    srv = ArtifactService()
    token = get_token("officer1")
    actor = auth_service.verify_access_token(token)

    # Mock artifact with malicious content reference attempting path traversal
    malicious_ref = "../../etc/passwd"
    art = Artifact(
        artifact_id="ART-HACK-001",
        case_id="CASE-2026-001",
        evidence_id="EV-001",
        processing_job_id="JOB-001",
        filename="passwd",
        path_within_source="/etc/passwd",
        provenance_chain=ProvenanceEnvelope(
            case_id="CASE-2026-001",
            evidence_id="EV-001",
            processing_job_id="JOB-001",
            engine_name="HACK_ENGINE",
            engine_version="1.0",
            source_reference="EV-001",
            observation_reference="HACK"
        ),
        content_reference=malicious_ref
    )
    srv.repository.save(art)

    with pytest.raises(PermissionError) as exc_info:
        srv.get_artifact_content_path(actor, "CASE-2026-001", "ART-HACK-001")

    assert "PATH TRAVERSAL DENIED" in str(exc_info.value)


# ============================================================================
# 5. ORIGINAL EVIDENCE SHA-256 HASH PRESERVATION TEST
# ============================================================================

def test_slice6_original_evidence_sha256_remains_unchanged():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    
    file_bytes = b"SLICE 6 HASH PRESERVATION RAW IMAGE BYTES"
    data = {"evidence_name": "Slice 6 Hash Check", "evidence_type": "DISK_IMAGE"}
    files = {"file": ("slice6_hash.raw", io.BytesIO(file_bytes), "application/octet-stream")}

    res_upload = client.post("/api/v1/cases/CASE-2026-001/evidence", data=data, files=files, headers=headers)
    assert res_upload.status_code == 201
    original_sha256 = res_upload.json()["sha256"]

    ev_id = res_upload.json()["evidence_id"]
    job_id = run_processing_job(token, "CASE-2026-001", ev_id)

    # Ingest and query artifacts
    res_art = client.get(f"/api/v1/cases/CASE-2026-001/artifacts", headers=headers)
    assert res_art.status_code == 200

    # Verify original evidence SHA-256 integrity check returns INTACT
    res_verify = client.post(f"/api/v1/cases/CASE-2026-001/evidence/{ev_id}/verify", headers=headers)
    assert res_verify.status_code == 200
    v_data = res_verify.json()
    assert v_data["expected_sha256"] == original_sha256
    assert v_data["calculated_sha256"] == original_sha256
    assert v_data["integrity_status"] == "INTACT"
