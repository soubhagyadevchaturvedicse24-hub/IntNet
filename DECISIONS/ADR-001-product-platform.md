# ADR-001: Product Platform & Local Deployment Architecture

* **Status:** `[PROPOSED / OPEN]`  
* **Date:** 2026-09-05  
* **Decision Makers:** CRIMENET Engineering Team  

---

## 1. Context and Problem Statement
CRIMENET requires a responsive, explainable investigator workspace that operates primarily in local / on-premise law enforcement environments with offline capability. We need to establish the foundational backend API and frontend application stack.

---

## 2. Decision Drivers
* Local / offline execution on Windows and Linux workstations.
* Clean separation of frontend UI, asynchronous job execution, and backend analytical pipelines.
* Python native integration for ML and data forensics workflows.
* Strong typing and component ecosystem for complex graph visualization and evidence inspector panels.

---

## 3. Considered Options
* **Option A:** Python FastAPI Backend + React / TypeScript Frontend (Local Web Application).
* **Option B:** Monolithic Desktop Framework (Electron / PySide6 / PyQt).
* **Option C:** Pure Python Web Dashboard (Streamlit / Dash).

---

## 4. Proposed Outcome
* **Proposed Option:** **Option A (FastAPI + React/TypeScript)**  
* **Current Status:** `[PROPOSED / OPEN]` pending end-to-end vertical slice validation.

---

## 5. Evidence & Verification Required to Finalize
* Validation of asynchronous background job queue and WebSocket streaming from FastAPI to React during mock forensic ingestion.
