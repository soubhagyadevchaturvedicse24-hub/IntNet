"""
Unit Tests for Entity Resolution Module
Validates normalizers, candidate matchers, resolver provenance preservation, and Kùzu graph ingestion.
"""

import pytest
import os, sys, shutil
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.entity_resolution.normalizer import (
    normalize_person_name, normalize_phone_number,
    normalize_vehicle_plate, normalize_location, normalize_organization
)
from src.entity_resolution.matcher import evaluate_candidate_match
from src.entity_resolution.resolver import EntityResolver
from src.entity_resolution.graph_integrator import KuzuEntityGraphIntegrator

def test_normalization_rules():
    assert normalize_person_name("Vikram  Singh") == "Vikram Singh"
    assert normalize_person_name("Mr. Vikram Singh") == "Vikram Singh"
    assert normalize_person_name("VIKRAM SINGH") == "Vikram Singh"
    
    assert normalize_phone_number("+91 98765 43210") == "+919876543210"
    assert normalize_phone_number("9876543210") == "+919876543210"
    assert normalize_phone_number("+91-98765-43210") == "+919876543210"
    
    assert normalize_vehicle_plate("DL-01-AB-1234") == "DL01AB1234"
    assert normalize_vehicle_plate("dl 01 ab 1234") == "DL01AB1234"
    
    assert normalize_location("Connaught Place, Zone-1") == "Connaught Place Zone 1"
    assert normalize_organization("Enterprise Pvt Ltd") == "Enterprise"

def test_candidate_matching_rules():
    # Exact Match
    m_class, conf, rule = evaluate_candidate_match("Vikram Singh", "Vikram Singh", "Person")
    assert m_class == "EXACT_MATCH"
    assert conf == 1.00
    
    # Ambiguous Initial Match
    m_class, conf, rule = evaluate_candidate_match("V. Singh", "Vikram Singh", "Person")
    assert m_class == "AMBIGUOUS_CANDIDATE"
    assert "HUMAN_REVIEW" in rule
    
    # Distinct Non-Match
    m_class, conf, rule = evaluate_candidate_match("Vikram Singh", "Rajesh Kumar", "Person")
    assert m_class == "DISTINCT_NON_MATCH"

def test_entity_resolver_provenance():
    raw_obs = [
        {"obs_id": "EV-OBS-101", "entity_type": "Person", "raw_value": "Vikram Singh", "source_file": "contacts.db"},
        {"obs_id": "EV-OBS-102", "entity_type": "Person", "raw_value": "Vikram  Singh", "source_file": "fir.pdf"},
        {"obs_id": "EV-OBS-103", "entity_type": "Person", "raw_value": "VIKRAM SINGH", "source_file": "chat.json"}
    ]
    resolver = EntityResolver()
    clusters = resolver.resolve_observations(raw_obs)
    
    assert len(clusters) == 1
    c = clusters[0]
    assert c["canonical_name"] == "Vikram Singh"
    assert len(c["source_evidence_ids"]) == 3
    assert "EV-OBS-101" in c["source_evidence_ids"]
    assert "EV-OBS-102" in c["source_evidence_ids"]
    assert c["supporting_observations_count"] == 3

def test_kuzu_graph_integrator():
    import time
    integrator = KuzuEntityGraphIntegrator(f"BENCHMARKS/kuzu_test_er_db_{time.time_ns()}")
    integrator.setup()
    
    clusters = [{
        "canonical_entity_id": "CAN-PER-0001",
        "entity_type": "Person",
        "canonical_name": "Vikram Singh",
        "supporting_observations_count": 2
    }]
    count = integrator.ingest_canonical_entities(clusters)
    assert count == 1
    
    integrator.teardown()
