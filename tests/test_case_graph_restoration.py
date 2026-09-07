"""
Automated regression & validation tests for CRIMENET Crime Contact Network Restoration.
Verifies:
1. Server-side authentication and BOLA authorization on case graph endpoints.
2. Real case-scoped graph query for CASE-2026-001 (returns Case Anchor, is_empty=True, 0 fake contacts).
3. Case Anchor domain integration (correct role and anchor ID per case).
4. People Contact Network projection (Person entities only).
5. Explicit demo mode toggle (?demo=true) with [DEMO MODE] disclaimer.
6. Case-scoped inspection endpoints (entity, relationship, neighbors, shortest path).
7. Human lead verification persistence and audit trail generation.
8. Elimination of fake entity fallback injection in ingestion pipeline.
"""

import io
import time
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.auth.service import AuthService

client = TestClient(app)
auth_service = AuthService()


def get_token(username: str) -> str:
    if username == "officer1":
        pwd = "OfficerPass123!"
    elif username == "officer2":
        pwd = "OfficerPass456!"
    elif username == "boss1":
        pwd = "HigherAuthPass789!"
    else:
        pwd = "OfficerPass123!"

    res = client.post("/api/v1/auth/login", json={"username": username, "password": pwd})
    assert res.status_code == 200, f"Login failed for {username}: {res.json()}"
    return res.json()["access_token"]


# ============================================================================
# 1. AUTHENTICATION & BOLA AUTHORIZATION
# ============================================================================

def test_unauthenticated_case_graph_access_denied():
    """Unauthenticated request to case graph must return 401 Unauthorized."""
    res = client.get("/api/v1/cases/CASE-2026-001/graph")
    assert res.status_code == 401


def test_cross_case_bola_graph_access_denied():
    """Officer 1 cannot access Officer 2's Case Graph (CASE-2026-002)."""
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/cases/CASE-2026-002/graph", headers=headers)
    assert res.status_code == 403
    assert "Officer not authorized for case" in res.json()["detail"]


# ============================================================================
# 2. REAL CASE DATA & HONEST EMPTY STATE (CASE-2026-001)
# ============================================================================

def test_real_case_graph_honest_empty_state():
    """
    CASE-2026-001 currently has real evidence artifacts (PDFs, images) but 0 extracted
    person-to-person relationships. The system must honestly report is_empty=True,
    display the Case Anchor node, and NOT silently fabricate contacts or substitute Vikram Singh.
    """
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/cases/CASE-2026-001/graph", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["case_id"] == "CASE-2026-001"
    assert data["demo_mode"] is False
    assert data["is_empty"] is True
    assert "No real contact-network relationships are currently available" in data["message"]
    
    # Case Anchor must be present
    assert "anchor" in data
    assert data["anchor"]["id"] == "ANC-2026-001"
    assert data["anchor"]["label"] == "Operation Cyber Net Target"
    assert data["anchor"]["role"] == "Investigation Subject"
    assert data["anchor"]["layer"] == 0

    # Nodes must contain only the Case Anchor
    assert len(data["nodes"]) == 1
    assert data["nodes"][0]["id"] == "ANC-2026-001"
    assert data["nodes"][0]["is_anchor"] is True
    assert data["edges"] == []

    # Must NOT contain fake Vikram Singh in real mode
    node_labels = [n.get("label", "") for n in data["nodes"]]
    assert "Vikram Singh" not in node_labels


def test_case_anchor_roles_differentiated_per_case():
    """Case anchors must reflect domain definitions (Subject vs Victim vs Other), not hardcoded roles."""
    token_boss = get_token("boss1")  # Boss has access to all cases
    headers = {"Authorization": f"Bearer {token_boss}"}

    # Case 1: Investigation Subject
    res1 = client.get("/api/v1/cases/CASE-2026-001/graph", headers=headers)
    assert res1.status_code == 200
    assert res1.json()["anchor"]["role"] == "Investigation Subject"

    # Case 2: Victim
    res2 = client.get("/api/v1/cases/CASE-2026-002/graph", headers=headers)
    assert res2.status_code == 200
    assert res2.json()["anchor"]["role"] == "Victim"

    # Case 3: Other
    res3 = client.get("/api/v1/cases/CASE-2026-003/graph", headers=headers)
    assert res3.status_code == 200
    assert res3.json()["anchor"]["role"] == "Other"


# ============================================================================
# 3. EXPLICIT DEMO MODE TOGGLE (?demo=true)
# ============================================================================

def test_explicit_demo_mode_toggle():
    """When ?demo=true is explicitly provided, return the demonstration contact network."""
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/cases/CASE-2026-001/graph?demo=true", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["case_id"] == "CASE-2026-001"
    assert data["demo_mode"] is True
    assert data["is_empty"] is False
    assert "[DEMO MODE]" in data["disclaimer"]
    assert data["anchor"]["id"] == "CAN-PER-0001"
    assert data["anchor"]["label"] == "Vikram Singh"

    # People Contact Network only: Every node must be Person
    for n in data["nodes"]:
        assert n["entity_type"] == "Person", f"Node {n['id']} has invalid entity_type {n['entity_type']}"

    # Verify concentric layers exist
    layers = {n["layer"] for n in data["nodes"]}
    assert 0 in layers  # Central anchor
    assert 1 in layers  # Direct associates
    assert 2 in layers  # Broader network
    assert 3 in layers  # Extended network

    # Edges must retain CCC scores and relationship types
    assert len(data["edges"]) > 0
    for e in data["edges"]:
        assert "ccc_score" in e
        assert "relationship_type" in e
        assert e["relationship_type"] == "ASSOCIATED_WITH"


# ============================================================================
# 4. CASE-SCOPED INSPECTION ENDPOINTS
# ============================================================================

def test_case_anchor_entity_details():
    """Querying entity details for Case Anchor returns valid anchor metadata."""
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/cases/CASE-2026-001/graph/entity/ANC-2026-001", headers=headers)
    assert res.status_code == 200
    d = res.json()
    assert d["canonical_entity_id"] == "ANC-2026-001"
    assert d["canonical_name"] == "Operation Cyber Net Target"
    assert d["role"] == "Investigation Subject"
    assert d["is_anchor"] is True
    assert d["match_method"] == "CASE_ANCHOR_DECLARATION"


def test_demo_entity_details_inspection():
    """Querying entity details in demo mode returns full canonical details."""
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/cases/CASE-2026-001/graph/entity/CAN-PER-0001?demo=true", headers=headers)
    assert res.status_code == 200
    d = res.json()
    assert d["canonical_entity_id"] == "CAN-PER-0001"
    assert d["canonical_name"] == "Vikram Singh"
    assert "human_verification_status" in d


def test_demo_relationship_details_inspection():
    """Querying relationship details in demo mode returns CCC breakdown & evidence references."""
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/cases/CASE-2026-001/graph/relationship/EDGE-0001?demo=true", headers=headers)
    assert res.status_code == 200
    d = res.json()
    assert d["edge_id"] == "EDGE-0001"
    assert "association_score" in d
    assert "ccc_ring" in d
    assert "supporting_evidence_id" in d


def test_demo_neighbors_and_shortest_path():
    """Test 1-hop neighbors and shortest path computation in case graph."""
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}

    # Neighbors
    res_nbr = client.get("/api/v1/cases/CASE-2026-001/graph/neighbors/CAN-PER-0001?hops=1&demo=true", headers=headers)
    assert res_nbr.status_code == 200
    assert res_nbr.json()["neighbor_count"] > 0

    # Shortest path
    res_path = client.get("/api/v1/cases/CASE-2026-001/graph/shortest_path?src_id=CAN-PER-0001&tgt_id=CAN-PER-0002&demo=true", headers=headers)
    assert res_path.status_code == 200
    assert res_path.json()["path_length"] == 1
    assert res_path.json()["path_nodes"] == ["CAN-PER-0001", "CAN-PER-0002"]


# ============================================================================
# 5. HUMAN LEAD VERIFICATION WORKFLOW
# ============================================================================

def test_human_lead_verification_persistence():
    """Human verification status logged via POST /verify must persist across subsequent queries."""
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}

    # Verify Anchor
    res_v = client.post(
        "/api/v1/cases/CASE-2026-001/graph/verify",
        json={"target_id": "ANC-2026-001", "status_decision": "HUMAN_VERIFIED_LEAD", "notes": "Verified by Lead Investigator"},
        headers=headers
    )
    assert res_v.status_code == 200
    assert res_v.json()["human_verification_status"] == "HUMAN_VERIFIED_LEAD"

    # Query back entity
    res_ent = client.get("/api/v1/cases/CASE-2026-001/graph/entity/ANC-2026-001", headers=headers)
    assert res_ent.status_code == 200
    assert res_ent.json()["human_verification_status"] == "HUMAN_VERIFIED_LEAD"


# ============================================================================
# 6. ELIMINATION OF FAKE ENTITY FALLBACK
# ============================================================================

def test_ingest_with_no_extracted_entities_does_not_inject_fake_vikram():
    """When a job produces 0 extracted entities, ingestion must NOT inject fake Vikram Singh fallback."""
    from src.api.graph_resolution_routes import entity_graph_service as svc
    from src.auth.models import TokenPayload, UserRole

    actor = TokenPayload(
        sub="USER-OFFICER-001",
        username="officer1",
        role=UserRole.INVESTIGATION_OFFICER,
        exp=int(time.time()) + 3600,
        jti="test-jti-001"
    )

    orig_get_job = svc.processing_service.get_job
    orig_get_contract = svc.processing_service.get_evidence_contract

    class MockJob:
        case_id = "CASE-2026-001"
        def model_dump(self):
            return {"case_id": "CASE-2026-001"}

    try:
        svc.processing_service.get_job = lambda a, j: MockJob()
        svc.processing_service.get_evidence_contract = lambda a, j: {
            "extracted_entities": [],
            "observed_artifacts": [],
            "provenance_envelope": {"evidence_id": "EV-TEST-001"}
        }

        res = svc.ingest_evidence_contract(actor, "CASE-2026-001", "JOB-TEST-EMPTY")
        assert res["status"] == "COMPLETED"
        assert res["canonical_entities_created"] == 0
        assert res["relationships_created"] == 0
        assert res["canonical_entities"] == []
        assert res["relationships"] == []
    finally:
        svc.processing_service.get_job = orig_get_job
        svc.processing_service.get_evidence_contract = orig_get_contract
