# ADR-007: Entity Resolution & Record Linkage Engine

* **Status:** `[PROPOSED / OPEN]`  
* **Date:** 2026-09-05  
* **Decision Makers:** CRIMENET Engineering Team  

---

## 1. Context and Problem Statement
Forensic evidence and FIR records contain noisy, duplicated entities (names with typographical/phonetic variations, phone numbers formatted differently, partial addresses) that must be deduplicated into canonical property graph nodes.

---

## 2. Decision Drivers
* High precision and recall on fuzzy entity records.
* In-process execution with zero separate daemon services.
* Low memory overhead during pairwise comparison.
* Seamless integration into `EvidenceContract_v1`.

---

## 3. Considered Options
* **Option A:** Splink (Probabilistic Fellegi-Sunter record linkage over embedded DuckDB).
* **Option B:** Deterministic Rule Engine + Levenshtein / Soundex normalizer.
* **Option C:** External Graph Entity Resolution Service (e.g. Senzing).

---

## 4. Current Status
* **Status:** `[PROPOSED / OPEN]` — Phase 3 Entity Resolution vertical slice completed and validated on initial entity types (`Person`, `PhoneNumber`, `Vehicle`, `Location`, `Organization`). Report saved at [`BENCHMARKS/reports/entity_resolution_eval_report.json`](file:///D:/Proto%20SIH/BENCHMARKS/reports/entity_resolution_eval_report.json).

---

## 5. Phase 3 Empirical Evaluation Results
* **Input Dataset:** [`DATA/fixtures/ER_EVALUATION_DATASET.json`](file:///D:/Proto%20SIH/DATA/fixtures/ER_EVALUATION_DATASET.json) (15 raw observations, exact duplicates, formatting variations, ambiguous candidates).
* **Evaluation Metrics:**
  * **Precision:** `1.0000`
  * **Recall:** `1.0000`
  * **F1-Score:** `1.0000`
  * **Resolution Latency:** `1.012 ms`
* **Graph Ingestion:** Successfully ingested resolved Canonical Entities and evidence-backed relationships into prototype Kùzu Graph database ([`BENCHMARKS/kuzu_resolved_graph_db`](file:///D:/Proto%20SIH/BENCHMARKS/kuzu_resolved_graph_db)).
* **Provenance Preservation:** 100% of canonical entities retain `source_evidence_ids`, `observed_values`, `normalized_value`, `match_confidence`, and `match_method`.

---

## 6. Architecture & Next Evaluation Steps
* **Current Baseline:** Rule-based normalizer + candidate matcher (`src/entity_resolution/`).
* **Future Upgrade:** Maintain architecture ready for Splink probabilistic linkage evaluation when scaling to multi-million record datasets.

