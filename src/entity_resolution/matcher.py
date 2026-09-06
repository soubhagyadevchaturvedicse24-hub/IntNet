"""
Candidate Matching Engine for Entity Resolution
Evaluates similarity between normalized entities and emits candidate match classifications with confidence scores.
"""

from difflib import SequenceMatcher
from typing import Tuple

def string_similarity(s1: str, s2: str) -> float:
    if not s1 or not s2:
        return 0.0
    return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

def is_initial_match(name1: str, name2: str) -> bool:
    """Checks if one name is an initial version of another (e.g. 'V. Singh' vs 'Vikram Singh')."""
    tokens1 = name1.split()
    tokens2 = name2.split()
    if len(tokens1) < 2 or len(tokens2) < 2:
        return False
    
    # Compare last names
    if string_similarity(tokens1[-1], tokens2[-1]) < 0.85:
        return False
        
    # Check first initial match
    f1, f2 = tokens1[0], tokens2[0]
    if len(f1) == 1 or len(f2) == 1:
        return f1[0].upper() == f2[0].upper()
    return False

def evaluate_candidate_match(norm_val1: str, norm_val2: str, entity_type: str) -> Tuple[str, float, str]:
    """
    Evaluates candidate similarity.
    Returns: (match_class, confidence_score, rule_name)
    Match Classes:
      - EXACT_MATCH (1.00)
      - HIGH_CONFIDENCE_FUZZY (0.85 - 0.99)
      - AMBIGUOUS_CANDIDATE (0.60 - 0.84) -> Flagged for Human Verification
      - DISTINCT_NON_MATCH (< 0.60)
    """
    if not norm_val1 or not norm_val2:
        return "DISTINCT_NON_MATCH", 0.0, "EMPTY_VALUE"
        
    if norm_val1 == norm_val2:
        return "EXACT_MATCH", 1.00, f"EXACT_NORMALIZED_{entity_type.upper()}"
        
    sim = string_similarity(norm_val1, norm_val2)
    
    # Check initial abbreviation match for Person names
    if entity_type.upper() == "PERSON" and is_initial_match(norm_val1, norm_val2):
        return "AMBIGUOUS_CANDIDATE", 0.75, "PERSON_INITIAL_MATCH_HUMAN_REVIEW_REQUIRED"
        
    if sim >= 0.85:
        return "HIGH_CONFIDENCE_FUZZY", round(sim, 2), "FUZZY_STRING_SIMILARITY"
    elif sim >= 0.60:
        return "AMBIGUOUS_CANDIDATE", round(sim, 2), "AMBIGUOUS_SIMILARITY_HUMAN_REVIEW_REQUIRED"
    else:
        return "DISTINCT_NON_MATCH", round(sim, 2), "NO_MATCH"
