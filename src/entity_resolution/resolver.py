"""
Canonical Entity Resolver Engine
Processes raw evidence observations, resolves duplicate references into Canonical Entities,
and preserves complete provenance across Evidence Contract source items.
"""

from typing import List, Dict, Any
from src.entity_resolution.normalizer import normalize_entity
from src.entity_resolution.matcher import evaluate_candidate_match

class EntityResolver:
    def __init__(self):
        self.canonical_entities: Dict[str, Dict[str, Any]] = {}
        self.canonical_counter = 1

    def resolve_observations(self, raw_observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Resolves a list of raw observations into Canonical Entities.
        Each observation dict expected format:
          {"obs_id": "EV-OBS-101", "entity_type": "Person", "raw_value": "Vikram  Singh", "source_file": "contacts.db"}
        """
        resolved_clusters: List[Dict[str, Any]] = []

        for obs in raw_observations:
            etype = obs.get("entity_type", "Unknown")
            raw_val = obs.get("raw_value", "")
            obs_id = obs.get("obs_id", f"OBS-{self.canonical_counter}")
            source_ref = obs.get("source_file", "unknown")
            
            norm_val = normalize_entity(etype, raw_val)
            
            matched_cluster = None
            highest_conf = 0.0
            best_match_class = "DISTINCT_NON_MATCH"
            best_rule = ""

            # Compare against existing canonical clusters
            for cluster in resolved_clusters:
                if cluster["entity_type"].upper() != etype.upper():
                    continue
                    
                match_class, conf, rule = evaluate_candidate_match(norm_val, cluster["normalized_value"], etype)
                
                # Merge if EXACT or HIGH_CONFIDENCE_FUZZY
                if match_class in ["EXACT_MATCH", "HIGH_CONFIDENCE_FUZZY"] and conf > highest_conf:
                    matched_cluster = cluster
                    highest_conf = conf
                    best_match_class = match_class
                    best_rule = rule

            if matched_cluster:
                # Merge into existing cluster
                matched_cluster["observed_values"].append(raw_val)
                matched_cluster["source_evidence_ids"].append(obs_id)
                matched_cluster["supporting_sources"].append(source_ref)
                matched_cluster["supporting_observations_count"] += 1
                if highest_conf < matched_cluster["match_confidence"]:
                    matched_cluster["match_confidence"] = highest_conf
                    matched_cluster["match_method"] = best_rule
            else:
                # Create new Canonical Entity Cluster
                cid = f"CAN-{etype[:3].upper()}-{self.canonical_counter:04d}"
                self.canonical_counter += 1
                
                new_cluster = {
                    "canonical_entity_id": cid,
                    "entity_type": etype,
                    "canonical_name": norm_val,
                    "normalized_value": norm_val,
                    "observed_values": [raw_val],
                    "source_evidence_ids": [obs_id],
                    "supporting_sources": [source_ref],
                    "match_confidence": 1.00,
                    "match_method": "NEW_CANONICAL_ROOT",
                    "supporting_observations_count": 1,
                    "human_verification_status": "UNVERIFIED_AUTOMATED_CLUSTER"
                }
                resolved_clusters.append(new_cluster)

        return resolved_clusters
