# Evaluation Specification: Splink Probabilistic Entity Resolution

**Document Version:** 1.0.0  
**Status:** `[PROPOSED / OPEN]` (Investigation & Evaluation Specification)  
**Date:** 2026-09-05  
**Target Technology:** **Splink (DuckDB Backend)** vs **Deterministic Rule Engine**  
**Role in Architecture:** Processing Layer — Entity Resolution & Cross-Source Record Linkage  

---

## 1. Objective
To evaluate whether **Splink** (an open-source probabilistic record linkage library implementing Fellegi-Sunter methodology over DuckDB) can accurately, efficiently, and maintainably deduplicate and resolve entities (People, Phone Numbers, Vehicles, Locations) across noisy synthetic forensic artifacts and synthetic FIR records without requiring external infrastructure.

---

## 2. Hypothesis
* *Hypothesis 1:* Splink running embedded on DuckDB can resolve typographical, phonetic, and formatting variations in names and phone numbers with significantly higher recall than deterministic string matching.
* *Hypothesis 2:* Splink's in-process DuckDB execution maintains minimal memory footprint ($< 500\text{ MB}$) and fast execution ($< 2.0\text{ seconds}$ on 20k records), making it ideal for our single-node local prototype.

---

## 3. Dataset / Fixture
* **Synthetic Entity Resolution Dataset (`SYN-ENTITIES-20K`):**
  * Total Records: 20,000 entity records with 3,000 planted duplicate pairs featuring controlled synthetic noise:
    * Typographical noise (1–2 character substitutions, missing spaces).
    * Phonetic variations (Soundex/Metaphone name alternatives common in Indian FIRs).
    * Missing/partial attributes (e.g., missing address prefix, phone with/without `+91`).
  * Deterministic Seed: `seed=20260905`.
  * Checksum: `sha256:3a7e58f01b92c4311099f654b9d073998b3c82e2cf573887c2b4a0c8413f1737`.

---

## 4. Environment
* **Host Runtime:** Python 3.12 x64.
* **Backend Database Engine:** Embedded `duckdb` (no standalone server process).
* **Library:** `splink>=3.9.0`.
* **Hardware:** 4 CPU cores, 8 GB RAM allocation.

---

## 5. Procedure
1. **Data Ingestion:** Load 20,000 synthetic entity rows into an in-memory DuckDB table.
2. **Track A: Deterministic Rule Engine:**
   * Run exact match + basic Levenshtein distance ($threshold \le 2$) on normalized fields.
   * Record execution time, precision, recall, and F1-score against ground truth.
3. **Track B: Splink Fellegi-Sunter Model:**
   * Configure blocking rules on primary keys (e.g., phonetic name match, exact phone prefix).
   * Define comparison levels for `name` (Jaro-Winkler + Levenshtein), `phone` (exact + partial), `address` (Levenshtein).
   * Execute `linker.predict()` with match probability threshold $\ge 0.85$.
   * Cluster resolved entities using `linker.cluster_pairwise_predictions_at_threshold()`.
   * Record execution time, precision, recall, and F1-score against ground truth.
4. **Evidence Contract Integration Verification:**
   * Test serialization of resolved canonical entity IDs and cluster confidence back into `EvidenceContract_v1` entities array.

---

## 6. Metrics (Mapped to Methodology)
* **Correctness:** Precision, Recall, F1-Score, and False Positive Rate on ground truth duplicate clusters.
* **Performance:** Total link & cluster execution time (seconds), records processed per second.
* **Resource Usage:** Peak memory usage during DuckDB blocking and pairwise scoring.
* **Integration Effort:** Simplicity of Python configuration and ease of exporting cluster assignments into property graph nodes.

---

## 7. Repetitions
* 5 consecutive runs with randomized entity order.

---

## 8. Expected Output
* Evaluation results log (`RESEARCH/reports/splink_evaluation_report.json`).
* Precision-Recall curve across varying match probability thresholds.

---

## 9. Acceptance Criteria
* **Resolution Accuracy:** $\text{F1-Score} \ge 0.95$ on synthetic noisy dataset.
* **Execution Latency:** Complete 20,000 record deduplication in $< 5.0\text{ seconds}$ on CPU.
* **Zero Infrastructure:** Operates 100% in-process via embedded DuckDB without running external daemon containers.

---

## 10. Threats to Validity
* Synthetic noise distributions may differ from real-world Indian police FIR and forensic extraction inconsistencies.
* Unsupervised parameter tuning vs supervised ground truth availability.

---

## 11. What Result Would Change the Architectural Decision
* **Adopt Splink as Standard if:** Splink achieves $> 15\%$ higher recall on noisy records than deterministic rules while running in $< 5\text{ seconds}$ on local DuckDB.
* **Retain Simple Rule Engine if:** Splink configuration overhead is disproportionate for prototype datasets, or if simpler deterministic normalization achieves acceptable precision/recall.
