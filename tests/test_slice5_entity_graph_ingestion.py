"""
Comprehensive Security, Entity Resolution, Kùzu Graph Construction, and Domain Test Suite for CRIMENET Slice 5.
Tests EvidenceContract_v1 ingestion into Kùzu Graph DB, canonical entity resolution, evidence traceability,
idempotent ingestion, BOLA cross-case graph isolation, entity/relationship ID manipulation defense,
human lead verification workflow, and audit log generation.
"""

import io
import time
import pytest
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
    else:
        pwd = password

    res = client.post("/api/v1/auth/login", json={"username": username, "password": pwd})
    assert res.status_code == 200, f"Login failed for {username}: {res.json()}"
    return res.json()["access_token"]


def create_completed_processing_job(token: str, case_id: str = "CASE-2026-001") -> str:
    headers = {"Authorization": f"Bearer {token}"}
    file_bytes = b"FORENSIC IMAGE BYTES FOR SLICE 5 GRAPH INGESTION TEST Vikram Singh +919876543210 test@investigation.org"
    data = {"evidence_name": f"Slice 5 Graph Disk {time.time()}", "evidence_type": "DISK_IMAGE"}
    files = {"file": ("graph_disk.raw", io.BytesIO(file_bytes), "application/octet-stream")}
    
    res_ev = client.post(f"/api/v1/cases/{case_id}/evidence", data=data, files=files, headers=headers)
    assert res_ev.status_code == 201
    ev_id = res_ev.json()["evidence_id"]

    res_proc = client.post(f"/api/v1/cases/{case_id}/evidence/{ev_id}/process", headers=headers)
    assert res_proc.status_code == 202
    job_id = res_proc.json()["job_id"]

    # Poll until job completes
    for _ in range(30):
        res_j = client.get(f"/api/v1/processing/jobs/{job_id}", headers=headers)
        if res_j.json()["status"] == "COMPLETED":
            break
        time.sleep(0.1)

    return job_id


# ============================================================================
# 1. EVIDENCE CONTRACT INGESTION & GRAPH CONSTRUCTION TESTS
# ============================================================================

def test_evidence_contract_graph_ingestion_success():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    job_id = create_completed_processing_job(token, "CASE-2026-001")

    # Ingest EvidenceContract into Case Graph
    res_ingest = client.post(f"/api/v1/cases/CASE-2026-001/graph/ingest/{job_id}", headers=headers)
    assert res_ingest.status_code == 201
    ingest_data = res_ingest.json()

    assert ingest_data["status"] == "COMPLETED"
    assert ingest_data["case_id"] == "CASE-2026-001"
    assert ingest_data["canonical_entities_created"] > 0
    assert "canonical_entities" in ingest_data
    assert "relationships" in ingest_data


def test_case_graph_query_success():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    
    res = client.get("/api/v1/cases/CASE-2026-001/graph", headers=headers)
    assert res.status_code == 200
    graph_data = res.json()
    assert graph_data["case_id"] == "CASE-2026-001"
    assert "nodes" in graph_data
    assert "edges" in graph_data


# ============================================================================
# 2. IDEMPOTENT INGESTION TEST
# ============================================================================

def test_idempotent_duplicate_ingestion():
    """Ingesting the same processing contract twice must be idempotent."""
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    job_id = create_completed_processing_job(token, "CASE-2026-001")

    # First Ingest
    res1 = client.post(f"/api/v1/cases/CASE-2026-001/graph/ingest/{job_id}", headers=headers)
    assert res1.status_code == 201
    c_count1 = res1.json()["canonical_entities_created"]

    # Second Ingest (Duplicate)
    res2 = client.post(f"/api/v1/cases/CASE-2026-001/graph/ingest/{job_id}", headers=headers)
    assert res2.status_code == 201
    c_count2 = res2.json()["canonical_entities_created"]

    # Entity count derived deterministically remains equal
    assert c_count1 == c_count2


# ============================================================================
# 3. CRITICAL SECURITY TESTS: BOLA & CROSS-CASE ISOLATION
# ============================================================================

def test_cross_case_graph_access_denied():
    """BOLA Attack: Officer 1 attempting to query Officer 2's Case Graph."""
    token1 = get_token("officer1")
    headers1 = {"Authorization": f"Bearer {token1}"}
    
    res = client.get("/api/v1/cases/CASE-2026-002/graph", headers=headers1)
    assert res.status_code == 403
    assert "Officer not authorized for case" in res.json()["detail"]


def test_cross_case_job_ingest_denied():
    """Adversarial Attack: Ingesting Officer 2's job into Case 1."""
    token2 = get_token("officer2")
    job2_id = create_completed_processing_job(token2, "CASE-2026-002")

    token1 = get_token("officer1")
    headers1 = {"Authorization": f"Bearer {token1}"}

    res = client.post(f"/api/v1/cases/CASE-2026-001/graph/ingest/{job2_id}", headers=headers1)
    assert res.status_code == 403
    assert "DENY" in res.json()["detail"]


def test_entity_id_manipulation_cross_case_denied():
    """Critical Security Test: Attempting to query or verify an Entity ID belonging to another case."""
    token2 = get_token("officer2")
    job2_id = create_completed_processing_job(token2, "CASE-2026-002")
    res_ing2 = client.post(f"/api/v1/cases/CASE-2026-002/graph/ingest/{job2_id}", headers={"Authorization": f"Bearer {token2}"})
    ent2_id = res_ing2.json()["canonical_entities"][0]["canonical_entity_id"]

    token1 = get_token("officer1")
    headers1 = {"Authorization": f"Bearer {token1}"}

    # Officer 1 attempts to verify Officer 2's entity ID under Case 1
    res_hack = client.post(f"/api/v1/cases/CASE-2026-001/graph/verify", json={"target_id": ent2_id, "status_decision": "HUMAN_VERIFIED_LEAD"}, headers=headers1)
    assert res_hack.status_code == 403
    assert "ID MANIPULATION DENY" in res_hack.json()["detail"] or "BOLA DENY" in res_hack.json()["detail"]


# ============================================================================
# 4. HUMAN VERIFICATION WORKFLOW TESTS
# ============================================================================

def test_human_lead_verification_workflow():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    job_id = create_completed_processing_job(token, "CASE-2026-001")
    
    res_ing = client.post(f"/api/v1/cases/CASE-2026-001/graph/ingest/{job_id}", headers=headers)
    ent_id = res_ing.json()["canonical_entities"][0]["canonical_entity_id"]

    # Verify Human Lead Decision
    payload = {
        "target_id": ent_id,
        "status_decision": "HUMAN_VERIFIED_LEAD",
        "notes": "Verified against external field intelligence report."
    }
    res_v = client.post("/api/v1/cases/CASE-2026-001/graph/verify", json=payload, headers=headers)
    assert res_v.status_code == 200
    assert res_v.json()["human_verification_status"] == "HUMAN_VERIFIED_LEAD"


def test_invalid_human_verification_status_rejected():
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "target_id": "CAN-PER-9999",
        "status_decision": "CONFIRMED_GUILTY"  # Disallowed non-analytical term
    }
    res = client.post("/api/v1/cases/CASE-2026-001/graph/verify", json=payload, headers=headers)
    assert res.status_code == 400
    assert "Invalid human verification status" in res.json()["detail"]


# ============================================================================
# 5. AUDIT TRAIL LOGGING FOR GRAPH OPERATIONS
# ============================================================================

def test_graph_operations_generate_audit_trail():
    token = get_token("boss1")
    headers = {"Authorization": f"Bearer {token}"}
    
    res = client.get("/api/v1/audit/logs", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["integrity_chain_valid"] is True
    
    actions = [e["action"] for e in data["events"]]
    assert "ENTITY_RESOLUTION_PERFORMED" in actions or "HUMAN_VERIFICATION_RECORDED" in actions or "READ_CASE_GRAPH" in actions
