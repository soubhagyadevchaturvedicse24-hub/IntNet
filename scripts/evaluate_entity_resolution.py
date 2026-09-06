"""
CRIMENET Phase 3 — Entity Resolution Evaluation Runner
Evaluates the rule-based entity resolution pipeline against DATA/fixtures/ER_EVALUATION_DATASET.json.
Generates evaluation metrics (Precision, Recall, F1, True Matches, False Matches, Missed Matches)
and ingests resolved Canonical Entities into Kùzu Graph database.
"""

import os
import sys
import json
import time
from typing import Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.entity_resolution.resolver import EntityResolver
from src.entity_resolution.graph_integrator import KuzuEntityGraphIntegrator

def run_er_evaluation():
    print("=== CRIMENET PHASE 3 — ENTITY RESOLUTION EVALUATION ===")
    
    dataset_path = "DATA/fixtures/ER_EVALUATION_DATASET.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        eval_ds = json.load(f)
        
    ground_truth_clusters = eval_ds["ground_truth_clusters"]
    
    # Flatten raw observations for resolution input
    raw_obs_list = []
    expected_pairs = set()  # Set of (obs_id1, obs_id2) expected to match
    
    for cluster in ground_truth_clusters:
        etype = cluster["entity_type"]
        obs_list = cluster["observations"]
        
        # Add to raw observation stream
        for o in obs_list:
            raw_obs_list.append({
                "obs_id": o["obs_id"],
                "entity_type": etype,
                "raw_value": o["raw_value"],
                "source_file": o["source_file"]
            })
            
        # Record ground truth pair matches (excluding ambiguous/distinct ones)
        if not cluster.get("is_ambiguous") and not cluster.get("is_distinct") and len(obs_list) > 1:
            for i in range(len(obs_list)):
                for j in range(i + 1, len(obs_list)):
                    id1, id2 = sorted([obs_list[i]["obs_id"], obs_list[j]["obs_id"]])
                    expected_pairs.add((id1, id2))

    # Execute Entity Resolution
    resolver = EntityResolver()
    start_t = time.time()
    resolved_clusters = resolver.resolve_observations(raw_obs_list)
    resolution_time_ms = round((time.time() - start_t) * 1000, 3)
    
    # Extract predicted pairs
    predicted_pairs = set()
    for rc in resolved_clusters:
        sources = rc["source_evidence_ids"]
        if len(sources) > 1:
            for i in range(len(sources)):
                for j in range(i + 1, len(sources)):
                    id1, id2 = sorted([sources[i], sources[j]])
                    predicted_pairs.add((id1, id2))
                    
    # Calculate Precision, Recall, F1
    true_matches = len(predicted_pairs.intersection(expected_pairs))
    false_matches = len(predicted_pairs - expected_pairs)
    missed_matches = len(expected_pairs - predicted_pairs)
    
    precision = true_matches / (true_matches + false_matches) if (true_matches + false_matches) > 0 else 1.0
    recall = true_matches / (true_matches + missed_matches) if (true_matches + missed_matches) > 0 else 1.0
    f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    print(f"Total Raw Observations Processed: {len(raw_obs_list)}")
    print(f"Canonical Clusters Emitted: {len(resolved_clusters)}")
    print(f"True Matches: {true_matches}, False Matches: {false_matches}, Missed Matches: {missed_matches}")
    print(f"Precision: {precision:.4f}, Recall: {recall:.4f}, F1-Score: {f1_score:.4f}")
    print(f"Resolution Time: {resolution_time_ms} ms")

    # Ingest Resolved Canonical Entities into Kùzu Graph
    integrator = KuzuEntityGraphIntegrator("BENCHMARKS/kuzu_resolved_graph_db")
    integrator.setup()
    nodes_ingested = integrator.ingest_canonical_entities(resolved_clusters)
    
    # Create sample evidence-backed relationships
    sample_rels = [
        {"src_id": "CAN-PER-0001", "tgt_id": "CAN-PHO-0003", "src_label": "Person", "tgt_label": "PhoneNumber", "rel_label": "USED_PHONE", "evidence_id": "EV-CONTRACT-2026-9001", "confidence": 1.0},
        {"src_id": "CAN-PER-0001", "tgt_id": "CAN-VEH-0004", "src_label": "Person", "tgt_label": "Vehicle", "rel_label": "USED_VEHICLE", "evidence_id": "EV-CONTRACT-2026-9002", "confidence": 1.0},
        {"src_id": "CAN-PER-0001", "tgt_id": "CAN-LOC-0005", "src_label": "Person", "tgt_label": "Location", "rel_label": "VISITED", "evidence_id": "EV-CONTRACT-2026-9003", "confidence": 1.0},
        {"src_id": "CAN-PER-0001", "tgt_id": "CAN-PER-0002", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9004", "confidence": 0.85}
    ]
    rels_ingested = integrator.ingest_resolved_relationships(sample_rels)
    integrator.teardown()

    # Build Evaluation Report
    report = {
        "document_version": "1.0.0",
        "phase": "Phase 3 — Entity Resolution Vertical Slice",
        "execution_timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evaluation_metrics": {
            "total_raw_observations": len(raw_obs_list),
            "canonical_clusters_resolved": len(resolved_clusters),
            "true_matches": true_matches,
            "false_matches": false_matches,
            "missed_matches": missed_matches,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1_score, 4),
            "resolution_duration_ms": resolution_time_ms
        },
        "graph_integration_status": {
            "target_database": "Kùzu Embedded Cypher (BENCHMARKS/kuzu_resolved_graph_db)",
            "canonical_nodes_ingested": nodes_ingested,
            "evidence_backed_relationships_ingested": rels_ingested
        },
        "resolved_canonical_entities": resolved_clusters
    }
    
    report_path = "BENCHMARKS/reports/entity_resolution_eval_report.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    print(f"Report saved to: {os.path.abspath(report_path)}")

if __name__ == "__main__":
    run_er_evaluation()
