"""
Deterministic Critical Contact & Association (CCC) Scorer
Calculates explainable Association Scores and Concentric Ring classifications for investigator decision support.
"""

import math
from typing import Dict, List, Any

RELATIONSHIP_BASE_WEIGHTS = {
    "CALLED": 1.00,
    "USED_PHONE": 0.80,
    "USED_VEHICLE": 0.75,
    "ASSOCIATED_WITH": 0.65,
    "CONNECTED_TO": 0.50,
    "VISITED": 0.40,
    "PARTICIPATED_IN": 0.40
}

def calculate_ccc_score(
    rel_type: str,
    frequency: int = 1,
    days_elapsed: float = 0.0,
    source_count: int = 1,
    er_confidence: float = 1.0,
    provenance_valid: bool = True,
    evidence_ids: List[str] = None
) -> Dict[str, Any]:
    if evidence_ids is None:
        evidence_ids = []

    # 1. Base Weight (25%)
    base_weight = RELATIONSHIP_BASE_WEIGHTS.get(rel_type.upper(), 0.40)
    f1 = 25.0 * base_weight

    # 2. Frequency Factor (25%)
    freq_factor = min(1.0, math.log(1 + frequency) / math.log(15))
    f2 = 25.0 * freq_factor

    # 3. Recency Decay (25%)
    recency_factor = math.exp(-days_elapsed / 30.0)
    f3 = 25.0 * recency_factor

    # 4. Multi-Source Proof (25%)
    source_factor = min(1.0, 0.25 + (0.25 * source_count))
    f4 = 25.0 * source_factor

    # Base Score Sum
    raw_score = (f1 + f2 + f3 + f4)

    # Multipliers
    c_er = max(0.50, min(1.00, er_confidence))
    c_prov = 1.00 if provenance_valid else 0.50

    final_score = int(round(min(100.0, raw_score * c_er * c_prov)))

    # Concentric Ring Classification
    if final_score > 75:
        ring = "RED"
        priority_label = "Highest-Priority Analytical Lead"
    elif final_score >= 41:
        ring = "YELLOW"
        priority_label = "Moderate-Priority Potential Association"
    else:
        ring = "GREEN"
        priority_label = "Lower-Priority Contextual Link"

    # Explanation Generator
    indicators = []
    indicators.append(f"Relationship Type Weight: {rel_type} (Base: {base_weight*100:.0f}%)")
    indicators.append(f"Frequency Count: {frequency} interactions recorded")
    indicators.append(f"Recency: Recorded {days_elapsed:.1f} days ago (Decay: {recency_factor*100:.0f}%)")
    indicators.append(f"Independent Sources: {source_count} distinct artifacts")
    indicators.append(f"Entity Resolution Match Confidence: {er_confidence*100:.0f}%")
    indicators.append(f"Provenance Integrity: {'Verified Cryptographic SHA-256' if provenance_valid else 'Unverified / Degraded'}")

    return {
        "association_score": final_score,
        "concentric_ring": ring,
        "priority_label": priority_label,
        "contributing_indicators": indicators,
        "supporting_evidence_ids": evidence_ids,
        "responsible_ai_notice": "Analytical score for investigator decision-support only. Not a probability of guilt or criminal risk rating.",
        "threshold_status": "WORKING / EXPERIMENTAL"
    }
