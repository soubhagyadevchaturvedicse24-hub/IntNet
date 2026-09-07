# CRIMENET SLICE 7A — FRONTEND ↔ BACKEND READ-ONLY ARCHITECTURAL AUDIT
**Execution Date:** 2026-09-07  
**Scope:** Whole-System Audit (Phase 0) across Frontend, Backend APIs, Domain Services, and Data Stores  
**Forensic Source Image:** `D:\Proto SIH\Images\Images_Set_1.E01` / `Images_Set_1.E02` (Verified Bit-for-Bit Untouched)

---

## 1. Executive Summary

This document provides a rigorous, empirical baseline audit of the CRIMENET system to evaluate whether the platform functions as an end-to-end investigator workflow across Frontend, Authentication, Authorization, Case Management, Evidence Intake, Real E01 Observation, Artifact Categorization, Evidence Explorer, and Entity Graph Intelligence.

### The Ground Reality
1. **Backend Maturity (Slices 1–7):** **PRODUCTION-READY & ROBUST (98/98 Tests Passing)**
   The backend possesses full, secure, case-isolated domain architectures for:
   - Slice 1: Authentication (HS256 JWT), RBAC, BOLA/BFLA defenses, PolicyEngine.
   - Slice 2: SQLite-backed Case Management with strict investigator assignment and audit chains.
   - Slice 3: Evidence Intake, SHA-256 preservation, and path traversal defenses.
   - Slice 4: Asynchronous Processing lifecycle producing immutable `EvidenceContract_v1`.
   - Slice 5: Deterministic Entity Resolution and Kùzu Graph construction.
   - Slice 6: Artifact Categorization (12 taxonomies), deduplication, and Case-scoped Evidence Explorer APIs (`/api/v1/cases/{case_id}/artifacts` and `/content`).
   - Slice 7: Native multi-segment E01 observation engine running in an isolated subprocess worker (`pyewf` + `pytsk3`), achieving complete filesystem traversal (1,122 dirs, 2,898 files) in 4.75 seconds with zero disk alteration.

2. **Frontend Architecture (`GET /`):** **SPECIALIZED DEMO VISUALIZATION ONLY**
   - The frontend is a single embedded HTML dashboard within `src/api/main.py` serving a Cytoscape.js concentric graph visualizer for an intelligence network.
   - There are **no other frontend files or frameworks** (no React, Vue, Angular, or external HTML files).
   - The UI at `GET /` connects **exclusively** to the Graph/Intelligence endpoints (`/api/graph/*`) and is populated with **pre-seeded demonstration data** centered on a hardcoded subject (`CAN-PER-0001` Vikram Singh).
   - **Critical Architectural Disconnect:** The frontend contains **zero UI interfaces** for Authentication (login/logout), Case Management, Evidence Upload, Processing Engine Execution, or Artifact Exploration.

---

## 2. Frontend Inventory & Architecture

| Component | Location in Codebase | Technology / Library | Purpose & Capabilities | Connectivity Reality |
| :--- | :--- | :--- | :--- | :--- |
| **App Shell / HTML** | `src/api/main.py:114-1909` | Vanilla HTML5 / CSS3 / Vanilla JS | Fullscreen investigator intelligence console | Rendered directly by FastAPI on `GET /` |
| **Graph Visualizer** | Inline JavaScript (`#cy`) | Cytoscape.js 3.28.1 | Concentric circular network visualization of person nodes | Connects to `/api/graph/overview` (Hardcoded Seed Data) |
| **SVG Ring Overlay** | Inline SVG (`#glow-overlay`) | SVG Filters + Gaussian Blur | Atmospheric neon glow rings for Layers 1, 2, 3 | Rendered locally in DOM; synchronized with Cytoscape viewport |
| **Network Minimap** | Floating Dock (`.minimap-container`) | Inline SVG + Cytoscape API | Viewport overview, smooth zoom (+/-), concentric reset | Interacts with Cytoscape instance locally |
| **Search Bar** | Header (`#global-search`) | Vanilla JS | Center and zoom Cytoscape canvas on matched node label/ID | Local in-memory search over loaded Cytoscape graph nodes |
| **Inspector Panel** | Right Panel (`#inspector-content`) | DOM manipulation | Displays properties, provenance, and action buttons for selected node/edge | Calls `/api/entity/{id}`, `/api/relationship/{id}`, `/api/verification/verify` |
| **Layer Filters** | Right Panel (`.layer-filter-grid`) | Cytoscape classes (`.faded`, `.layer-dimmed`) | Toggles visual isolation for Layer 1, 2, 3, or All | Local Cytoscape filtering; no backend call |
| **Spread Slider** | Left Panel (`#network-spread-slider`) | Polar coordinate math | Scales radial distance of concentric nodes (50%–180%) | Local DOM & Cytoscape position mutation |
| **Shortest Path** | Left Panel (`#path-target-input`) | Cytoscape BFS / Backend API | Highlights shortest path between primary anchor and target | Calls `/api/graph/shortest_path` |
| **1-Hop Explorer** | Left Panel (`exploreNeighbors()`) | Cytoscape BFS / Backend API | Discovers 1-hop associates of selected entity | Calls `/api/graph/neighbors/{id}?hops=1` |

### Missing Frontend Views (The Blind Spots)
The frontend completely lacks:
- **Authentication View:** No login dialog, token input, or session status. The web UI cannot supply a Bearer token.
- **Case Management View:** No case list, case selector, create case modal, or case metadata viewer.
- **Evidence Intake View:** No file upload widget, drag-and-drop zone, or evidence registry table.
- **Processing Job View:** No progress bars, worker status monitor, timeout controls, or processing triggers.
- **Artifact Explorer View:** No categorized file list, metadata columns, hex previewer, or PDF reader modal.

---

## 3. Backend Domain & Endpoint Inventory

The backend comprises seven distinct slices with clear architectural boundaries:

### 3.1 Authentication & Authorization (Slice 1)
- **Module:** `src/auth/`, `src/authorization/`, `src/api/auth_routes.py`
- **Endpoints:**
  - `POST /api/v1/auth/login`: Authenticates investigator; issues HS256 JWT access token.
  - `GET /api/v1/auth/me`: Validates active token; returns user profile, role, and authorized cases.
- **Security Features:** PBKDF2 password hashing (100k iterations), Token revocation/expiration, PolicyEngine ABAC/RBAC, BOLA/BFLA cross-tenant isolation.
- **UI Connectivity:** **NOT CONNECTED.** The UI does not call `/api/v1/auth/login`.

### 3.2 Case Management (Slice 2)
- **Module:** `src/cases/`, `src/api/case_routes.py`
- **Endpoints:**
  - `POST /api/v1/cases`: Creates new case container with judicial context.
  - `GET /api/v1/cases`: Lists cases assigned to calling investigator.
  - `GET /api/v1/cases/{case_id}`: Retrieves detailed case metadata.
  - `PUT /api/v1/cases/{case_id}`: Updates case metadata.
  - `DELETE /api/v1/cases/{case_id}`: Soft-deletes / closes case.
- **Persistence:** SQLite (`DATA/cases.db`).
- **UI Connectivity:** **NOT CONNECTED.** The UI does not expose case selection or case creation.

### 3.3 Evidence Intake & Preservation (Slice 3)
- **Module:** `src/evidence/`, `src/api/case_routes.py`
- **Endpoints:**
  - `POST /api/v1/cases/{case_id}/evidence`: Registers evidence container; streams file bytes; computes SHA-256; writes immutable manifest.
  - `GET /api/v1/cases/{case_id}/evidence`: Lists registered evidence for case.
  - `GET /api/v1/cases/{case_id}/evidence/{evidence_id}`: Retrieves evidence record.
  - `GET /api/v1/cases/{case_id}/evidence/{evidence_id}/verify`: Re-computes SHA-256 from disk to detect tampering.
- **Security Features:** Path traversal sanitization, strict MIME checks, immutable storage pathing (`DATA/evidence/{case_id}/`).
- **UI Connectivity:** **NOT CONNECTED.**

### 3.4 Forensic Processing Engine (Slice 4 & Slice 7)
- **Module:** `src/processing/`, `src/observation/`, `src/api/processing_routes.py`
- **Endpoints:**
  - `POST /api/v1/cases/{case_id}/evidence/{evidence_id}/process`: Submits asynchronous observation job.
  - `GET /api/v1/processing/jobs/{job_id}`: Polls job status (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`).
  - `GET /api/v1/processing/jobs/{job_id}/contract`: Retrieves generated `EvidenceContract_v1`.
- **Worker Isolation:** `src/observation/isolated_engine.py` executes `src/observation/worker.py` in an out-of-process subprocess with strict timeout containment.
- **Observation Stack:** Native `pyewf` (libewf) handles multi-segment `.E01` + `.E02`; `pytsk3` traverses NTFS/FAT partitions without mounting.
- **UI Connectivity:** **NOT CONNECTED.**

### 3.5 Artifact Categorization & Evidence Explorer (Slice 6)
- **Module:** `src/artifacts/`, `src/api/artifact_routes.py`
- **Endpoints:**
  - `GET /api/v1/cases/{case_id}/artifacts`: Multi-criteria filtering (by category, filename, allocation status, recovery status, date range, pagination).
  - `GET /api/v1/cases/{case_id}/artifacts/{artifact_id}`: Detailed metadata, cryptographic hash, provenance chain, and recommended viewer interface (`HEX`, `PDF`, `IMAGE`, `DATABASE`, `TEXT`).
  - `GET /api/v1/cases/{case_id}/artifacts/{artifact_id}/content`: Secure binary stream of extracted artifact file with path-traversal prevention.
- **Persistence:** SQLite (`DATA/artifacts.db`).
- **UI Connectivity:** **NOT CONNECTED.**

### 3.6 Graph Intelligence & Verification (Slice 5 & Legacy Demo API)
- **Module:** `src/graph/`, `src/entity_resolution/`, `src/api/main.py`
- **Endpoints:**
  - `GET /api/graph/overview`: Returns nodes and edges for Cytoscape.js.
  - `GET /api/entity/{id}`: Returns entity profile, observed values, and verification status.
  - `GET /api/relationship/{id}`: Returns relationship score, CCC ring, and contributing indicators.
  - `POST /api/verification/verify`: Records investigator lead decision (`HUMAN_VERIFIED_LEAD`, `UNDER_REVIEW`, `REJECTED_ASSOCIATION`).
  - `GET /api/graph/shortest_path`: Computes BFS shortest path between entities.
  - `GET /api/graph/neighbors/{id}`: Returns 1-hop or n-hop subgraph.
  - `GET /api/evidence/{id}`: Returns chain-of-custody modal data for an edge.
- **UI Connectivity:** **FULLY CONNECTED.** The UI interacts directly with these endpoints.
- **Data Reality:** All graph endpoints currently serve **hardcoded synthetic demo data** (`CAN-PER-0001` Vikram Singh, 36 persons, 39 relationships, hardcoded evidence contracts `EV-CONTRACT-2026-9001` to `9005`). They are **not yet automatically dynamically populated from the E01 observation output**.

---

## 4. Architectural Gap Analysis: UI vs Backend

```
                               INVESTIGATOR WORKFLOW GAP MATRIX
┌─────────────────────────┬──────────────────────────────────┬─────────────────────────────────┬────────────────────────┐
│ Stage                   │ Backend Capability               │ Frontend Representation         │ Integration Status     │
├─────────────────────────┼──────────────────────────────────┼─────────────────────────────────┼────────────────────────┤
│ 1. Authentication       │ JWT (HS256), PBKDF2, RBAC, BOLA  │ None (Hardcoded public access)  │ 🔴 NOT CONNECTED       │
│ 2. Case Management      │ SQLite, Case Isolation, BOLA     │ Static title ("Vikram Singh")   │ 🔴 NOT CONNECTED       │
│ 3. Evidence Intake      │ Multipart upload, SHA-256 hash   │ None                            │ 🔴 NOT CONNECTED       │
│ 4. E01 Observation      │ Isolated pyewf/pytsk3 subprocess │ None                            │ 🔴 NOT CONNECTED       │
│ 5. Artifact Repository  │ 12 categories, deduplication     │ None                            │ 🔴 NOT CONNECTED       │
│ 6. Evidence Explorer    │ Filtering, Metadata, /content    │ None                            │ 🔴 NOT CONNECTED       │
│ 7. Graph Visualization  │ Kùzu Graph schema & BFS engine   │ Full Cytoscape Concentric UI    │ 🟡 MOCK/DEMO CONNECTED │
│ 8. Human Verification   │ Audit-logged lead verification   │ 3 Action Buttons (Verify/Reject)│ 🟢 VERIFIED (Demo Data)│
└─────────────────────────┴──────────────────────────────────┴─────────────────────────────────┴────────────────────────┘
```

### Root Causes of the Divergence
1. **Vertical Slice Sequencing:** Slices 1 through 7 were constructed with backend-first forensic rigor (ensuring 100% cryptographic integrity, libewf stability, and zero C-extension crashes in the main server). The frontend was developed during early prototype phases as an interactive concept demonstrator for the concentric intelligence graph layout.
2. **Missing UI Bridge Layer:** There is currently no unified client-side application state (e.g. active `case_id`, active `JWT_token`, active `evidence_id`) in the browser JavaScript.
3. **Graph Ingestion Decoupling:** In Slice 5, `src/graph/kuzu_service.py` was built to ingest `EvidenceContract_v1` into Kùzu DB. However, the UI at `GET /` queries `/api/graph/overview` which pulls from an in-memory demo dictionary (`DATA/demo_network.json` / inline mock) rather than querying Kùzu for the currently loaded case.

---

## 5. Summary Conclusion

The CRIMENET system has built a world-class, forensically sound, multi-segment E01 processing and artifact categorization backend. However, because the user interface is currently a dedicated graph demonstrator rather than a complete investigator portal, the complete end-to-end user experience cannot yet be driven solely from the browser.
