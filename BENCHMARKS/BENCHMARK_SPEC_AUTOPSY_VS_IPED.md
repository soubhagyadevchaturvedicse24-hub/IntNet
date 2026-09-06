# Benchmark Specification: Autopsy vs IPED (Forensic Observation Layer)

**Document Version:** 1.0.0  
**Status:** `[PROPOSED / OPEN]` (Benchmark Specification)  
**Date:** 2026-09-05  
**Candidate Technologies:** **Autopsy (CLI Ingest)** vs **IPED (Digital Evidence Processor)**  

---

## 1. Objective
To empirically evaluate whether **Autopsy** or **IPED** is the more effective, reliable, and decoupled **Forensic Observation / Ingestion Engine** for populating the CRIMENET `EvidenceContract_v1` on a local Windows/Linux development environment.

---

## 2. Hypothesis
* *Hypothesis 1:* IPED achieves higher raw batch ingestion throughput and lower idle/active RAM usage on disk images than Autopsy.
* *Hypothesis 2:* Autopsy provides higher out-of-the-box metadata completeness for CASE-UCO/blackboard communication logs and EXIF photos without requiring custom parsing modules.

---

## 3. Dataset / Fixtures
* **Synthetic Disk Image Fixture (`SYN-IMAGE-01.E01` / `SYN-IMAGE-01.RAW`):**
  * Size: 5 GB synthetic FAT32/EXT4 disk image.
  * Contents: 200 JPEG photographs with EXIF GPS coordinates, 5 SQLite databases (Android contacts, call logs, SMS), 50 PDF/DOCX documents, 20 carved/deleted files.
  * Deterministic Checksum: `sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069`.

---

## 4. Environment
* **Host OS:** Windows 11 x64 (Primary) / Ubuntu 22.04 LTS (Secondary cross-check).
* **Hardware Limit:** 8 CPU cores, 16 GB RAM allocation.
* **Autopsy Version:** 4.21.0+ (CLI via `autopsy64.exe`).
* **IPED Version:** 4.0.0+ (CLI via `iped.exe` / `iped.jar`).

---

## 5. Procedure
1. **Pre-test State:** Clean target output directory; ensure background processes are quiescent.
2. **Execution Phase A (Autopsy):**
   * Invoke `autopsy64.exe --inputPath="SYN-IMAGE-01.E01" --caseName="bench_autopsy_01" --runFromCommandLine=true`.
   * Record CPU %, RAM usage, completion time, and UI window behavior.
   * Export CASE-UCO report and SQLite `autopsy.db`.
3. **Execution Phase B (IPED):**
   * Invoke IPED batch command: `iped -d SYN-IMAGE-01.E01 -o bench_iped_01`.
   * Record CPU %, RAM usage, completion time, and process exit status.
   * Export IPED JSON/CSV output.
4. **Contract Normalization Test:**
   * Run the Python `EvidenceNormalizer` against Autopsy outputs and IPED outputs to generate `EvidenceContract_v1` JSON.
   * Measure schema coverage and data transformation latency.

---

## 6. Metrics (Mapped to Methodology)
* **Performance:** Total ingest duration (seconds), files indexed per second.
* **Resource Usage:** Peak RAM (MB), average CPU utilization %.
* **Reliability:** Headless automation success (zero modal dialogs, deterministic exit code / completion signal).
* **Capability & Correctness:** Percentage of ground-truth artifacts successfully extracted (EXIF GPS, call records, deleted files).
* **Integration Effort:** Lines of code required in the Python Normalizer adapter for each engine.

---

## 7. Repetitions
* 3 complete cold runs per candidate tool with complete output directory wipe between runs.

---

## 8. Expected Output
* Benchmark execution log (`BENCHMARKS/reports/autopsy_vs_iped_report.json`).
* Normalized Evidence Contract JSONs produced from both engines for comparison.

---

## 9. Acceptance Criteria
* **Ingest Speed:** Complete 5 GB synthetic image ingest in under 15 minutes.
* **Metadata Extraction Parity:** $\ge 95\%$ extraction rate of ground-truth photo EXIF and call log records.
* **Automation:** 100% unattended completion without manual UI interaction.

---

## 10. Threats to Validity
* Autopsy GUI window launch on Windows may introduce minor OS window manager overhead.
* Java heap size configurations in IPED (`-Xmx`) vs Autopsy JVM settings may alter memory comparisons if not equalized.

---

## 11. What Result Would Change the Architectural Decision
* **Select IPED if:** IPED achieves $>2\times$ faster ingestion speed, runs completely silent without UI windows, and provides clean JSON/CSV export that maps $\ge 95\%$ into `EvidenceContract_v1`.
* **Retain Autopsy if:** IPED requires extensive custom coding to extract mobile SQLite artifacts, or if Autopsy's CASE-UCO and `autopsy.db` SQLite mapping is significantly more robust and complete.
