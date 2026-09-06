# ADR-003: Normalized Evidence Contract Decoupling Boundary

* **Status:** `[PROPOSED / OPEN]`  
* **Date:** 2026-09-05  
* **Decision Makers:** CRIMENET Engineering Team  

---

## 1. Context and Problem Statement
Downstream processing (facial recognition, entity resolution, CCC scoring, and graph database loading) must not depend directly on undocumented Autopsy SQLite tables or IPED internal data formats.

---

## 2. Decision Drivers
* Strict architectural decoupling between Observation and Analytics.
* Complete provenance preservation (source image path, byte offset, hash, timestamp).
* JSON Schema versioning (`1.0.0`) for maintainability.

---

## 3. Considered Options
* **Option A:** Explicit intermediate Normalized Evidence Contract (`EvidenceContract_v1` JSON).
* **Option B:** Direct SQL queries against Autopsy's SQLite database from the backend.
* **Option C:** Direct CASE-UCO RDF/JSON-LD consumption throughout the entire pipeline.

---

## 4. Current Status
* `[PROPOSED / OPEN]` — Specified in `RESEARCH/EVIDENCE_CONTRACT_V1.md`.

---

## 5. Evidence & Verification Required to Finalize
* Validation that `EvidenceContract_v1` successfully carries all necessary fields for the first vertical slice without missing provenance data.
