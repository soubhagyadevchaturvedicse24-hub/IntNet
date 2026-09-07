# CRIMENET SLICE 7A — FRONTEND BUTTON & ACTION FUNCTION MATRIX
**Execution Date:** 2026-09-07  
**Scope:** Exhaustive audit of all interactive elements on the frontend (`GET /`), along with the inverse inventory of missing investigator UI controls.

---

## 1. Classification Definitions

Every interactive element is strictly categorized according to the following standards:

- **`FACT`**: A purely verified technical or mathematical reality supported by direct empirical code and network trace.
- **`VERIFIED`**: Full end-to-end integration: clicking the element transmits an authorized backend request, executes a stateful operation, and renders persistent or dynamic backend results.
- **`PARTIALLY VERIFIED`**: The UI triggers an endpoint and receives a response, but either returns hardcoded/seeded demo data or executes client-side-only mutations without persistent backend synchronization.
- **`MOCK / DEMO`**: The element functions visually or calls an endpoint, but the data source is hardcoded synthetic demonstration data (e.g. Vikram Singh `CAN-PER-0001` seed data), disconnected from real E01 evidence ingestion.
- **`NOT CONNECTED`**: The element exists in the UI, is visually rendered or clickable, but has no backend route, has no event listener, or does not send any network request; OR the backend route exists but has no corresponding UI element.
- **`NOT IMPLEMENTED`**: Neither the UI control nor the backend endpoint exists anywhere in the codebase.
- **`UNKNOWN`**: Indeterminate or unverified behavior.

---

## 2. Interactive UI Element Matrix (Frontend at `GET /`)

| # | Element Label / Icon | Selector / Location | Expected Investigator Action | Actual Backend Call | Empirical Behavior Observed | Classification |
| :- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Global Search** | `#global-search` (Header) | Search suspects or entities in the active case | None (Client-side DOM) | Matches string against loaded Cytoscape nodes; centers & zooms on match. | **`FACT`** |
| **2** | **Notifications Bell** | Header Icon (Badge: "3") | View system alerts or worker job notices | None | Static SVG with hardcoded badge number 3; no click event listener attached. | **`NOT CONNECTED`** |
| **3** | **Reset Layout** | `.header-btn` (Header) | Reset graph layout to concentric circles | None (Cytoscape API) | Resets Cytoscape viewport and restores baseline concentric node coordinates. | **`FACT`** |
| **4** | **Fit Graph** | `.header-btn` (Header) | Fit entire network into visible canvas | None (Cytoscape API) | Calls `cy.animate({ fit: { padding: 40 } })` to adjust zoom and center canvas. | **`FACT`** |
| **5** | **Section Chevrons** | `.panel-sec-title` (Panels) | Expand/collapse accordion panel sections | None (Client DOM) | Toggles `style.display = 'none'` on sibling content card; rotates chevron 180°. | **`FACT`** |
| **6** | **Network Spread Slider**| `#network-spread-slider` (Left) | Adjust distance/spacing between concentric rings | None (Math calculation) | Recalculates polar coordinates `(r * scale, theta)` for all nodes; rescales SVG rings. | **`FACT`** |
| **7** | **Reset Full Graph** | `.btn-ctrl` (Left Panel) | Reset layout and reset spread slider to 100% | None (Cytoscape API) | Resets spread slider to 100% and animates Cytoscape nodes back to initial radius. | **`FACT`** |
| **8** | **Find Shortest Path** | `.btn-ctrl` (Left Panel) | Find criminal connection path between 2 suspects | `GET /api/graph/shortest_path?src_id=...&tgt_id=...` | Returns path from seeded demo graph; dims unrelated nodes; displays alert box. | **`MOCK / DEMO`** |
| **9** | **Explore 1-Hop Neighbors**| `.btn-ctrl` (Left Panel) | Expand immediate criminal associates | `GET /api/graph/neighbors/{id}?hops=1` | Queries demo graph API; alerts neighbor count and list of names. | **`MOCK / DEMO`** |
| **10**| **Zoom In (+)** | `.zoom-btn` (Minimap Dock) | Magnify network visualization canvas | None (Cytoscape API) | Multiplies zoom by 1.25 with ease-out cubic animation. | **`FACT`** |
| **11**| **Zoom Out (-)** | `.zoom-btn` (Minimap Dock) | Demagnify network visualization canvas | None (Cytoscape API) | Multiplies zoom by 0.8 with ease-out cubic animation. | **`FACT`** |
| **12**| **Reset Minimap (⛶)** | `.zoom-btn` (Minimap Dock) | Reset viewport from minimap | None (Cytoscape API) | Calls `resetConcentricLayout()`. | **`FACT`** |
| **13**| **Node Tap / Select** | `#cy` canvas (Node click) | Inspect entity profile and provenance | `GET /api/entity/{id}` | Highlights node neighborhood; renders properties and action buttons in Right Panel. | **`MOCK / DEMO`** |
| **14**| **Edge Tap / Select** | `#cy` canvas (Edge click) | Inspect relationship score and CCC indicators | `GET /api/relationship/{edgeId}` | Highlights edge & connected nodes; renders CCC ring & indicators in Right Panel. | **`MOCK / DEMO`** |
| **15**| **Canvas Tap (Clear)** | `#cy` canvas (Background click)| Deselect node/edge; un-dim network | None (Cytoscape API) | Removes `.faded` and `.highlighted` classes; restores active layer filter. | **`FACT`** |
| **16**| **Under Review** | `.btn-review-lead` (Inspector) | Mark analytical lead as under active review | `POST /api/verification/verify` | Submits JSON body `{ entity_id, status: 'UNDER_REVIEW' }`; updates UI badge. | **`VERIFIED`** |
| **17**| **✓ Verify Lead** | `.btn-verify-lead` (Inspector) | Confirm criminal association as verified lead | `POST /api/verification/verify` | Submits JSON body `{ entity_id, status: 'HUMAN_VERIFIED_LEAD' }`; updates UI badge. | **`VERIFIED`** |
| **18**| **✕ Reject** | `.btn-reject-lead` (Inspector) | Reject false lead or coincidental association | `POST /api/verification/verify` | Submits JSON body `{ entity_id, status: 'REJECTED_ASSOCIATION' }`; updates UI badge. | **`VERIFIED`** |
| **19**| **View Chain of Custody**| `.btn-ctrl` (Edge Inspector) | View evidence hash, source file, timestamp | `GET /api/evidence/{evidenceId}` | Fetches demo evidence record; displays browser `alert()` with SHA-256 and source. | **`MOCK / DEMO`** |
| **20**| **Layer 1 Filter** | `#btn-filter-l1` (Right Panel) | Focus strictly on Direct Associates (Ring 1) | None (Cytoscape classes) | Adds `.layer-focused` to Layer 1 nodes; adds `.layer-dimmed` to Layers 2 & 3. | **`FACT`** |
| **21**| **Layer 2 Filter** | `#btn-filter-l2` (Right Panel) | Focus strictly on Broader Network (Ring 2) | None (Cytoscape classes) | Adds `.layer-focused` to Layer 2 nodes; adds `.layer-dimmed` to Layers 1 & 3. | **`FACT`** |
| **22**| **Layer 3 Filter** | `#btn-filter-l3` (Right Panel) | Focus strictly on Extended Network (Ring 3)| None (Cytoscape classes) | Adds `.layer-focused` to Layer 3 nodes; adds `.layer-dimmed` to Layers 1 & 2. | **`FACT`** |
| **23**| **Show All Filter** | `#btn-filter-all` (Right Panel)| Restore visibility to all layers | None (Cytoscape classes) | Removes all `.layer-dimmed` and `.layer-focused` classes. | **`FACT`** |

---

## 3. The Inverse Matrix: Missing Investigator UI Functions

The following table lists critical investigative functions supported by the CRIMENET backend that currently have **zero user interface buttons or controls** in the frontend:

| Subsystem | Missing Frontend UI Control | Corresponding Operational Backend Route | Impact on Investigator Workflow |
| :--- | :--- | :--- | :--- |
| **Auth** | Login / Logout Modal | `POST /api/v1/auth/login` | Investigator cannot log in or switch user roles from the browser. |
| **Auth** | Current User Profile Pill | `GET /api/v1/auth/me` | No visual indicator of active officer identity or authorized court level. |
| **Cases** | Create New Case Button | `POST /api/v1/cases` | Investigator cannot initialize a new case investigation from the UI. |
| **Cases** | Case Selector Dropdown | `GET /api/v1/cases` | Cannot switch between assigned cases (`CASE-2026-001`, `CASE-2026-002`). |
| **Cases** | Close / Archive Case Button | `DELETE /api/v1/cases/{case_id}` | Case status cannot be updated or archived from the UI. |
| **Evidence** | Evidence Ingestion Dropzone | `POST /api/v1/cases/{case_id}/evidence` | Forensic images (E01/RAW) cannot be uploaded or registered via the browser. |
| **Evidence** | Evidence Integrity Verifier | `GET /api/v1/cases/{case_id}/evidence/{id}/verify` | Cannot trigger on-demand SHA-256 integrity checks from the UI. |
| **Processing** | Start Observation Job Button| `POST /api/v1/cases/{case_id}/evidence/{id}/process` | Cannot launch isolated pyewf/pytsk3 observation worker from the UI. |
| **Processing** | Job Progress & Health Monitor| `GET /api/v1/processing/jobs/{job_id}` | Cannot observe worker progress, timeout warnings, or failure logs. |
| **Artifacts** | Evidence Explorer Table | `GET /api/v1/cases/{case_id}/artifacts` | Extracted files and partitions cannot be browsed, searched, or sorted. |
| **Artifacts** | Category Filter Tabs | `GET /api/v1/cases/{case_id}/artifacts?category=...` | Cannot filter extracted files by DOCUMENT, DATABASE, IMAGE, etc. |
| **Viewers** | PDF Document Viewer | `GET /api/v1/cases/{case_id}/artifacts/{id}/content` | Extracted PDF documents cannot be previewed in an inline reader modal. |
| **Viewers** | Raw Hex / Binary Viewer | `GET /api/v1/cases/{case_id}/artifacts/{id}/content` | Extracted disk headers, partitions, or MBR cannot be inspected in hex. |
| **Graph** | Ingest Evidence into Graph | `POST /api/v1/cases/{case_id}/graph/ingest` | Real E01 artifacts cannot be transformed into graph nodes from the UI. |

---

## 4. Empirical Evaluation Summary

1. **Working Frontend Features:**
   - Client-side graph interaction (smooth mouse-wheel zoom lerp, zoom buttons, concentric reset, spread slider, layer filter toggles, search navigation) is **100% functional and responsive**.
   - Lead verification action buttons (`verifyCurrentTarget`) successfully submit HTTP POST payloads to `/api/verification/verify` and dynamically update DOM badges.
2. **Key Limitation:**
   - All network graph data originates from a **static mock dataset** (`CAN-PER-0001` Vikram Singh).
   - Slices 1, 2, 3, 4, 6, and 7 exist as high-performance, thoroughly tested backend services, but have not yet been wired to UI components.
