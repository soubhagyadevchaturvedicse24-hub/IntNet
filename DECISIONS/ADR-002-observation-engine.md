# ADR-002: Forensic Observation & Extraction Engine

* **Status:** `[PROPOSED / OPEN]`  
* **Date:** 2026-09-05  
* **Decision Makers:** CRIMENET Engineering Team  

---

## 1. Context and Problem Statement
Forensic evidence images (E01, RAW) must be examined to extract raw artifacts, media files, and file system metadata without coupling downstream analytics to proprietary or internal forensic database schemas.

---

## 2. Decision Drivers
* Headless / CLI automation on Windows and Linux.
* Extraction coverage (EXIF, Android call/contact databases, carved pictures).
* Machine-readable export (CASE-UCO, SQLite, JSON).
* Decoupling from product analytics.

---

## 3. Considered Options
* **Option A:** Autopsy (CLI Ingestion + SQLite / CASE-UCO export).
* **Option B:** IPED (Digital Evidence Processor - Java CLI).
* **Option C:** Custom Sleuth Kit (`tsk_loaddb` / libtsk) Python wrapper.

---

## 4. Current Status
* `[PROPOSED / OPEN]` — Pending execution of `BENCHMARKS/BENCHMARK_SPEC_AUTOPSY_VS_IPED.md`.

---

## 5. Evidence & Verification Required to Finalize
* Empirical comparison of ingest duration, memory usage, headless execution reliability, and `EvidenceContract_v1` mapping coverage.
