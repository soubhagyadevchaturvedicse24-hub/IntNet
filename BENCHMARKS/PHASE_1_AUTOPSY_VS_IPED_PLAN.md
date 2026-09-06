# Phase 1 Benchmark Plan: Autopsy vs IPED Forensic Observation Layer

**Document Version:** 1.0.0  
**Status:** `[PROPOSAL / BENCHMARK PLAN]`  
**Date:** 2026-09-06  
**Candidate Technologies:** **Autopsy (CLI)** vs **IPED (Digital Evidence Processor)**  

---

## 1. Core Evaluation Principles

### A. Forensic Correctness Priority Rule
> [!CAUTION]
> **Performance alone must never determine the winner.**  
> A candidate engine that processes disk images faster but produces materially incomplete, inaccurate, or missing observations **must not be preferred or selected**. Correctness, artifact completeness, and provenance retention take absolute priority over raw ingestion speed.

### B. Immutable Fixture Principle
Both candidate tools will be evaluated against the exact same deterministic synthetic disk image fixture (`SYN-IMAGE-01.E01` / `RAW`, `seed=20260905`). The fixture must remain completely read-only and immutable throughout all benchmark runs.

### C. Sample Size & Measurement Distinction
The Phase 1 protocol uses $N=3$ cold runs per candidate engine.
* **Exploratory Feasibility Sample:** $N=3$ runs provide an initial feasibility measurement. Statistical significance (e.g. narrow confidence intervals) is **not** claimed from $N=3$.
* **Raw Observation Recording:** Every raw execution time, memory sample, CPU sample, and output file size is recorded explicitly in the benchmark report log.

---

## 2. The 12 Evaluation Criteria & Measurement Plan

| # | Criteria | Evaluation Method | Primary Metric / Unit |
|---|---|---|---|
| 1 | **Capability** | Verification of supported disk image formats (E01, RAW) and ingest features. | Feature checklist against Evidence Contract requirements |
| 2 | **Correctness** | Observed artifact values compared directly against `SYN-FORENSIC-GROUND-TRUTH-V1`. | Itemized Discrepancy & Error Count |
| 3 | **Artifact Completeness** | Qualitative classification of extracted vs missing ground-truth artifacts. | Discrepancy Severity Breakdown (Critical, Major, Minor, Info) |
| 4 | **Provenance Preservation** | Verification of source image path, byte offset, hash, and timestamps on all items. | Provenance Integrity Score (%) |
| 5 | **EvidenceContract_v1 Coverage** | Percentage of `EvidenceContract_v1` fields cleanly populated without null fallbacks. | Schema Completeness (%) |
| 6 | **Headless / CLI Reliability** | Process exit code, background execution, zero blocking modal dialogs. | Pass / Fail |
| 7 | **Processing Time** | Duration from process launch to complete output generation. | Seconds (Raw observations for 3 runs, P50/P95) |
| 8 | **Peak RAM** | Peak Resident Set Size (RSS) during active ingestion. | Megabytes (MB) |
| 9 | **CPU Utilization** | Average CPU % across physical/logical cores during ingest. | CPU Load % |
| 10 | **Output Size** | Total disk space consumed by engine case files, indices, and exports. | Megabytes (MB) |
| 11 | **Repeatability** | Consistency of output artifacts and runtime across sample runs. | Raw Observation Variance across $N=3$ runs |
| 12 | **Failure Behavior** | Handling of corrupted header blocks and invalid paths. | Graceful Error Logging Score |

---

## 3. Discrepancy Classification & Evaluation Framework

No hard-coded percentage threshold (such as >5% loss) is used for automatic disqualification. Instead, all missing or inaccurate observations are categorized using the following framework:

1. **Discrepancy Type:** Missing Artifact, Inaccurate Attribute, False Positive, or Broken Provenance.
2. **Severity Classification:**
   * **Critical:** Missing high-value investigative items (call logs, EXIF GPS fixes, suspect photos).
   * **Major:** Missing general filesystem metadata or unparsed document bodies.
   * **Minor:** Omission of secondary EXIF parameters (e.g. camera focal length).
   * **Informational:** Minor formatting or ISO timestamp string representation differences.
3. **Potential Decision Impact:** Evaluation of whether the discrepancy impacts crime linkage decision support and whether it can be mitigated via configuration or normalizer tuning.

---

## 4. Benchmark Execution Procedure

```text
[1. PRE-TEST SANITY CHECK]
       - Verify immutable synthetic fixture hash (SYN-IMAGE-01.E01)
       - Record host environment metadata (OS build, CPU, RAM, GPU)
       - Clear OS file system caches
               ↓
[2. CANDIDATE A EXECUTION (Autopsy CLI)]
       - Discover available output formats (autopsy.db, CASE-UCO JSON, etc.)
       - Execute N=3 cold runs (monitoring CPU %, Peak RAM, duration)
       - Run AutopsyBenchmarkAdapter -> emit EvidenceContract_v1 JSON
               ↓
[3. CANDIDATE B EXECUTION (IPED CLI)]
       - Discover available output formats (iped-output.json, CSVs, etc.)
       - Execute N=3 cold runs (monitoring CPU %, Peak RAM, duration)
       - Run IPEDBenchmarkAdapter -> emit EvidenceContract_v1 JSON
               ↓
[4. GROUND-TRUTH CORRECTNESS EVALUATION]
       - Compare EvidenceContract_v1 outputs against SYN-FORENSIC-GROUND-TRUTH-V1
       - Classify all discrepancies by Type, Severity, and Decision Impact
               ↓
[5. REPORT GENERATION]
       - Export phase1_autopsy_vs_iped_report.json for human ADR review
```

---

## 5. Artifact Output & Reporting

The execution of this benchmark plan produces a single comprehensive result artifact:
* `BENCHMARKS/reports/phase1_autopsy_vs_iped_report.json`

This report provides the full evidence base for human review under **`DECISIONS/ADR-002-observation-engine.md`**. No automatic technology selection will occur.
