"""
Unit Tests for FastAPI Investigator Graph API
Verifies API endpoints for graph overview, entity inspection, relationship details,
evidence traceability, neighbor lookup, shortest path, and human verification.
"""

import pytest
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_get_graph_overview():
    response = client.get("/api/graph/overview")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) >= 5

def test_get_entity_details():
    response = client.get("/api/entity/CAN-PER-0001")
    assert response.status_code == 200
    data = response.json()
    assert data["canonical_entity_id"] == "CAN-PER-0001"
    assert data["entity_type"] == "Person"
    assert "source_evidence_ids" in data

def test_get_relationship_details():
    ov = client.get("/api/graph/overview").json()
    edge_id = ov["edges"][0]["id"]
    
    response = client.get(f"/api/relationship/{edge_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["edge_id"] == edge_id
    assert "supporting_evidence_id" in data
    assert "association_score" in data
    assert "ccc_ring" in data
    assert "contributing_indicators" in data
    assert "responsible_ai_disclaimer" in data

def test_get_evidence_traceability():
    response = client.get("/api/evidence/EV-CONTRACT-2026-9001")
    assert response.status_code == 200
    data = response.json()
    assert data["traceability_status"] == "VERIFIED_CHAIN_OF_CUSTODY"
    assert data["evidence_record"]["source_artifact"] == "call_log.db"

def test_get_neighbors():
    response = client.get("/api/graph/neighbors/CAN-PER-0001?hops=1")
    assert response.status_code == 200
    data = response.json()
    assert data["root_entity_id"] == "CAN-PER-0001"
    assert "neighbors" in data

def test_get_shortest_path():
    response = client.get("/api/graph/shortest_path?src_id=CAN-PER-0001&tgt_id=CAN-PER-0002")
    assert response.status_code == 200
    data = response.json()
    assert data["source_id"] == "CAN-PER-0001"
    assert data["target_id"] == "CAN-PER-0002"
    assert data["path_length"] >= 1

def test_post_human_verification():
    payload = {
        "entity_id": "CAN-PER-0001",
        "status": "HUMAN_VERIFIED_LEAD",
        "notes": "Verified by lead investigator"
    }
    response = client.post("/api/verification/verify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["human_verification_status"] == "HUMAN_VERIFIED_LEAD"
