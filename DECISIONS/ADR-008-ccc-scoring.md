# ADR-008: Critical Contact & Association (CCC) Scoring Formulation

* **Status:** `[PROPOSED / OPEN]`  
* **Date:** 2026-09-06  
* **Decision Makers:** CRIMENET Engineering Team  

---

## 1. Context and Problem Statement
CRIMENET requires an explainable, deterministic scoring model to prioritize investigative attention across multi-modal evidence graphs. The scoring mechanism must answer: *"Which connections deserve investigator attention first, and why?"* without producing black-box machine learning predictions or automated labels of criminality.

---

## 2. Decision Drivers
* **Explainability:** 100% transparent factor breakdown emitting human-readable explanations.
* **Evidence Traceability:** Direct attachment of Evidence Contract observation IDs to computed scores.
* **Responsible AI:** Strict prohibition of "criminal risk" or "guilt probability" labels. Scores are classified purely as working analytical prioritization indicators.
* **Concentric Prioritization:** Classification into RED (Highest Priority), YELLOW (Moderate Priority), and GREEN (Lower Priority) working queues.

---

## 3. Considered Options
* **Option A:** Explainable Deterministic Weighted Factor Model ($S_{CCC} = \sum W_i F_i \times C_{ER} \times C_{Prov}$).
* **Option B:** Supervised Machine Learning Classifier (e.g. XGBoost / Random Forest).
* **Option C:** Graph Neural Network (GNN) link prediction model.

---

## 4. Current Status
* **Status:** `[PROPOSED / OPEN]` — Phase 5 CCC scoring formulation and validation completed. Option A selected for prototype baseline. Verified on [`DATA/fixtures/CCC_EVALUATION_DATASET.json`](file:///D:/Proto%20SIH/DATA/fixtures/CCC_EVALUATION_DATASET.json) (100% test pass rate across RED, YELLOW, GREEN test scenarios). Report saved at [`BENCHMARKS/reports/ccc_scoring_eval_report.json`](file:///D:/Proto%20SIH/BENCHMARKS/reports/ccc_scoring_eval_report.json).

---

## 5. Phase 5 Implementation & Verification Results
* **Formula:** $S_{CCC} = \min\left(100, \text{Round}\left( (25 F_1 + 25 F_2 + 25 F_3 + 25 F_4) \times C_{ER} \times C_{Prov} \right)\right)$
* **Working Concentric Rings:**
  * **RED Ring ($S_{CCC} > 75$):** Highest-Priority Analytical Leads
  * **YELLOW Ring ($41 \le S_{CCC} \le 75$):** Moderate-Priority Potential Associations
  * **GREEN Ring ($S_{CCC} \le 40$):** Lower-Priority Contextual Connections
* **Status:** Maintained as `[PROPOSED / OPEN]` pending operational feedback from investigator reviews.
