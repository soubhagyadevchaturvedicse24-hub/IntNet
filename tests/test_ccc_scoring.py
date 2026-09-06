"""
Unit Tests for CCC Scoring Engine
Verifies deterministic relationship scoring, concentric ring thresholds, and explanation generation.
"""

import pytest
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.analytics.ccc_scorer import calculate_ccc_score

def test_high_priority_red_ring():
    res = calculate_ccc_score(
        rel_type="CALLED",
        frequency=18,
        days_elapsed=2,
        source_count=3,
        er_confidence=1.00,
        provenance_valid=True,
        evidence_ids=["EV-CONTRACT-2026-9001", "EV-CONTRACT-2026-9002"]
    )
    assert res["concentric_ring"] == "RED"
    assert res["association_score"] >= 76
    assert len(res["contributing_indicators"]) == 6
    assert "EV-CONTRACT-2026-9001" in res["supporting_evidence_ids"]

def test_moderate_priority_yellow_ring():
    res = calculate_ccc_score(
        rel_type="USED_PHONE",
        frequency=4,
        days_elapsed=12,
        source_count=2,
        er_confidence=1.00,
        provenance_valid=True
    )
    assert res["concentric_ring"] == "YELLOW"
    assert 41 <= res["association_score"] <= 75

def test_low_priority_green_ring():
    res = calculate_ccc_score(
        rel_type="VISITED",
        frequency=1,
        days_elapsed=60,
        source_count=1,
        er_confidence=0.75,
        provenance_valid=True
    )
    assert res["concentric_ring"] == "GREEN"
    assert res["association_score"] <= 40

def test_unverified_provenance_degradation():
    res_valid = calculate_ccc_score(rel_type="CALLED", frequency=10, provenance_valid=True)
    res_degraded = calculate_ccc_score(rel_type="CALLED", frequency=10, provenance_valid=False)
    
    assert res_degraded["association_score"] < res_valid["association_score"]
