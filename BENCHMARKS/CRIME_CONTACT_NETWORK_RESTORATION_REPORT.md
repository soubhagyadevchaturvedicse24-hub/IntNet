# CRIMENET — CRITICAL REGRESSION FIX REPORT
## RESTORE EXISTING CRIME CONTACT NETWORK + CONNECT REAL DATA

**Date**: 2026-09-07  
**Status**: VALIDATED & OPERATIONAL  
**Test Suite**: 127/127 PASSED (116 Baseline + 11 Restoration Tests)

---

## 1. MANDATORY FINAL QUESTION ANSWER

> **"Is the Crime Contact Network now displaying real case-derived evidence data, or is it still displaying seeded/demo data?"**

### **DIRECT ANSWER: YES, IT NOW DISPLAYS REAL CASE-DERIVED EVIDENCE DATA BY DEFAULT.**

Specifically:
1. **Real Case Data Mode (Default)**:
   - When an investigator views `CASE-2026-001`, the Crime Contact Network queries the authenticated, case-scoped endpoint `GET /api/v1/cases/CASE-2026-001/graph` using the investigator's JWT token.
   - The central node rendered is the **Case Anchor** for `CASE-2026-001`: `ANC-2026-001 ("Operation Cyber Net Target", role: Investigation Subject)`.
   - Because real evidence ingested so far (E01 raw images, partition tables, files, emails, phone numbers) has produced **0 valid person-to-person relationships**, CRIMENET **honestly and accurately reports `is_empty: True`**.
   - It renders the isolated Case Anchor node alongside the clear banner:
     > `"REAL CASE DATA — CASE-2026-001"`  
     > `"No real contact-network relationships are currently available for this case."`
   - **No mock entities (e.g. Vikram Singh or Rahul Verma) are fabricated or silently substituted.**
2. **Explicit Demo Preview Mode (Opt-in Only)**:
   - A demonstration view of the multi-tier concentric network (`CAN-PER-0001 Vikram Singh`) is accessible **only** when explicitly toggled via `?demo=true` or the UI button `"Switch to Demo Preview"`.
   - When active, it displays a high-visibility amber banner:
     > `"[DEMO MODE] CAN-PER-0001 Vikram Singh contact network is pre-seeded demonstration data."`
   - It is never the default for any investigation case.

---

## 2. ROOT CAUSE ANALYSIS OF PREVIOUS REGRESSION

| # | Root Cause Component | Previous State | Fixed State |
|---|----------------------|----------------|-------------|
| 1 | **Frontend Data Source** | `workspace.html` hardwired `fetch('/api/graph/overview')` — an unauthenticated demo endpoint returning static mock data. | `workspace.html` calls `GET /api/v1/cases/${activeCaseId}/graph?demo=${isDemoMode}` with Bearer token authentication. |
| 2 | **Fake Ingestion Fallback** | `src/entity_resolution/service.py` lines 121–127 injected fake observations (`Vikram Singh`, `Rahul Verma`, `+919876543210`) whenever raw entities were empty. | Fallback eliminated entirely. Ingesting empty observations returns `0` canonical entities and `0` relationships. |
| 3 | **Visual Projection Scope** | Visual graph mixed non-human asset nodes (`PhoneNumber`, `Vehicle`, `Location`) as top-level nodes on canvas. | Visual projection strictly displays a **People Contact Network** (`Person` entities only). Asset evidence is preserved in the evidence inspector. |
| 4 | **Central Anchor Node** | Central node hardcoded as `CAN-PER-0001`. | Central node dynamically retrieves the domain `CaseAnchor` (`role: Investigation Subject`, `Victim`, or `Other`) from the active case. |
| 5 | **Case Anchor Persistence** | `SQLiteCaseRepository` did not serialize `anchor_json` or handle enum serialization properly. | Added `anchor_json` column, JSON-mode serialization, and deserialization into `CaseAnchor`. |
| 6 | **Kùzu Database Concurrency** | Repeated instantiations of `GraphIntelligenceService` caused file lock collisions (`RuntimeError: Could not set lock on file`). | Created global `shared_demo_graph_service` singleton, eliminating lock contention. |

---

## 3. ARCHITECTURE & SECURITY ENFORCEMENT

### 3.1 Authentication & PolicyEngine PDP Authorization (BOLA/BFLA)
- Endpoint: `/api/v1/cases/{case_id}/graph`
- All requests require a valid JWT `TokenPayload` via `get_current_user`.
- Authorization is evaluated through `PolicyEngine.evaluate()`:
  - **BOLA Defense**: Officer 1 attempting to query Officer 2's case graph (`CASE-2026-002`) receives `403 Forbidden` (`"BOLA DENY: Officer not authorized for case 'CASE-2026-002'"`).
  - **ID Manipulation Defense**: Attempting to verify or inspect an entity belonging to another case triggers an `ID MANIPULATION DENY`.
  - **Audit Logging**: All graph queries and human verifications are immutably recorded in the cryptographic audit log.

### 3.2 Dynamic Case Anchor Domain Model
Each case defines a tailored investigative anchor:
- `CASE-2026-001` (*Operation Cyber Net*): `ANC-2026-001`, *"Operation Cyber Net Target"*, `role: Investigation Subject`
- `CASE-2026-002` (*Operation Red Horizon*): `ANC-2026-002`, *"Operation Red Horizon Complainant"*, `role: Victim`
- `CASE-2026-003` (*Operation Closed Vault*): `ANC-2026-003`, *"Operation Closed Vault Lead"*, `role: Other`

### 3.3 Concentric Analytical Layers & CCC Scoring
- **Layer 0**: Central Case Anchor (`border-width: 3.5px`, white border, enlarged node).
- **Layer 1 (Direct Associates - Red)**: Deterministic 1-hop BFS neighbors from Case Anchor.
- **Layer 2 (Broader Network - Amber)**: 2-hop BFS neighbors from Case Anchor.
- **Layer 3 (Extended Network - Green)**: 3+ hop BFS neighbors from Case Anchor.
- **Edges**: Maintain evidence contract IDs, observation source artifact, SHA-256 provenance, verification status, and CCC Association Scores calculated via `calculate_ccc_score()`.

---

## 4. AUTOMATED TEST & VERIFICATION RESULTS

### Full Test Suite Execution:
```bash
python -m pytest -v
```
**Results: 127 passed, 0 failed, 0 errors in 42.35s**

| Test Module | Tests | Status | Scope |
|-------------|-------|--------|-------|
| `tests/test_case_graph_restoration.py` | 11 | **PASSED** | Authentication, BOLA, Case Anchor, Real Empty State, Demo Toggle, Inspection Endpoints, Human Lead Verification |
| `tests/test_api_graph.py` | 7 | **PASSED** | Legacy Graph API backwards compatibility |
| `tests/test_slice1_security_auth.py` | 11 | **PASSED** | JWT Authentication, RBAC, Role Escalation |
| `tests/test_slice2_case_management.py` | 13 | **PASSED** | Case CRUD, Judicial Context, Case Anchors |
| `tests/test_slice3_evidence_preservation.py` | 11 | **PASSED** | Storage, SHA-256 Immuntability, BOLA |
| `tests/test_slice4_processing_engine.py` | 9 | **PASSED** | Processing Jobs, Worker Lifecycle, Audit Logs |
| `tests/test_slice5_entity_graph_ingestion.py` | 9 | **PASSED** | Entity Resolution, Kùzu Ingestion, BOLA |
| `tests/test_slice6_artifact_explorer.py` | 11 | **PASSED** | Artifact Categorization, Explorer APIs |
| `tests/test_slice7_e01_observation.py` | 27 | **PASSED** | Real Multi-segment E01 Observation Engine |
| `tests/test_slice8a_deep_parsers.py` | 18 | **PASSED** | Deep Parsers (PDF, EXIF/Image, SQLite) |
| **TOTAL** | **127** | **100% PASS** | **Zero Regressions Across Entire CRIMENET Platform** |

---

## 5. SUMMARY OF CODE CHANGES

1. **`src/cases/models.py`**:
   - Added `AnchorRole` enum (`VICTIM`, `INVESTIGATION_SUBJECT`, `OTHER`) and `CaseAnchor` model.
   - Integrated `anchor: Optional[CaseAnchor]` into `Case` model.
2. **`src/cases/repository.py`**:
   - Updated `SQLiteCaseRepository` schema to persist `anchor_json` with JSON-mode serialization and deserialization.
3. **`src/cases/service.py`**:
   - Added default `CaseAnchor` instances for `CASE-2026-001`, `CASE-2026-002`, and `CASE-2026-003`.
4. **`src/entity_resolution/service.py`**:
   - Removed fake fallback entity injection (lines 121–127).
   - Refactored `get_case_graph(actor, case_id, demo=False)` to project People-only networks, compute BFS concentric layers from the Case Anchor, attach CCC scores, and support honest empty state.
   - Added case-scoped inspection helpers: `get_entity_details`, `get_relationship_details`, `get_neighbors`, `get_shortest_path`.
   - Enhanced `verify_human_lead` to persist verification decisions across queries.
5. **`src/api/graph_service.py`**:
   - Exported global `shared_demo_graph_service` singleton to prevent Kùzu concurrency file lock contention.
6. **`src/api/main.py`**:
   - Reused `shared_demo_graph_service` for legacy endpoints.
7. **`src/api/graph_resolution_routes.py`**:
   - Added case-scoped, authenticated routes:
     - `GET /api/v1/cases/{case_id}/graph?demo=false`
     - `GET /api/v1/cases/{case_id}/graph/entity/{entity_id}?demo=false`
     - `GET /api/v1/cases/{case_id}/graph/relationship/{edge_id}?demo=false`
     - `GET /api/v1/cases/{case_id}/graph/neighbors/{entity_id}?demo=false`
     - `GET /api/v1/cases/{case_id}/graph/shortest_path?demo=false`
     - `POST /api/v1/cases/{case_id}/graph/verify`
8. **`src/api/workspace.html`**:
   - Tied Network tab to `activeCaseId` and `currentToken`.
   - Added dynamic `network-banner` distinguishing Real Case Data vs Demo Preview.
   - Added canvas overlay for honest empty state.
   - Implemented dynamic Case Anchor styling (`node[layer = 0], node[?is_anchor]`) and layer color filters.
   - Rewired `inspectEntity`, `submitVerification`, `findShortestPath`, and `exploreNeighbors` to case-scoped authenticated APIs.
9. **`tests/test_case_graph_restoration.py`**:
   - 11 comprehensive automated tests covering all restoration requirements.
