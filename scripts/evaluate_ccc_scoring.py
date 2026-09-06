"""
CRIMENET Phase 5 — CCC Scoring Evaluation Runner
Evaluates the deterministic CCC scoring model against DATA/fixtures/CCC_EVALUATION_DATASET.json.
Generates evaluation report at BENCHMARKS/reports/ccc_scoring_eval_report.json.
"""

import os
import sys
import json
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.analytics.ccc_scorer import calculate_ccc_score

def run_ccc_evaluation():
    print("=== CRIMENET PHASE 5 — CCC SCORING EVALUATION ===")
    
    dataset_path = "DATA/fixtures/CCC_EVALUATION_DATASET.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        eval_ds = json.load(f)
        
    test_cases = eval_ds["test_relationships"]
    eval_results = []
    passed_cases = 0

    for tc in test_cases:
        score_res = calculate_ccc_score(
            rel_type=tc["rel_type"],
            frequency=tc["frequency"],
            days_elapsed=tc["days_elapsed"],
            source_count=tc["source_count"],
            er_confidence=tc["er_confidence"],
            provenance_valid=tc["provenance_valid"],
            evidence_ids=tc["evidence_ids"]
        )
        
        score = score_res["association_score"]
        ring = score_res["concentric_ring"]
        
        status = "PASSED"
        if ring != tc["expected_ring"]:
            status = "FAILED"
        if "min_expected_score" in tc and score < tc["min_expected_score"]:
            status = "FAILED"
        if "max_expected_score" in tc and score > tc["max_expected_score"]:
            status = "FAILED"

        if status == "PASSED":
            passed_cases += 1
            
        print(f"[{status}] {tc['name']} -> Score: {score}, Ring: {ring} (Expected: {tc['expected_ring']})")
        
        eval_results.append({
            "test_case_id": tc["test_case_id"],
            "name": tc["name"],
            "calculated_score": score,
            "calculated_ring": ring,
            "expected_ring": tc["expected_ring"],
            "status": status,
            "explanation": score_res["contributing_indicators"],
            "supporting_evidence_ids": score_res["supporting_evidence_ids"]
        })

    total = len(test_cases)
    print(f"\nResults: {passed_cases}/{total} Test Cases Passed.")

    report = {
        "document_version": "1.0.0",
        "phase": "Phase 5 — CCC Scoring Formulation",
        "execution_timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": {
            "total_test_cases": total,
            "passed_test_cases": passed_cases,
            "pass_rate_percent": round((passed_cases / total) * 100, 2)
        },
        "test_evaluations": eval_results
    }

    report_path = "BENCHMARKS/reports/ccc_scoring_eval_report.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    print(f"Report saved to: {os.path.abspath(report_path)}")

if __name__ == "__main__":
    run_ccc_evaluation()
