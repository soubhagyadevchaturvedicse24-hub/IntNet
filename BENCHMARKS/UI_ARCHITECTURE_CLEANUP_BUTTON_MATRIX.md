# CRIMENET — UI ARCHITECTURE CLEANUP
## FUNCTIONAL BUTTON & INTERACTION MATRIX

**Platform**: CRIMENET Forensic Intelligence Lab  
**Module**: Investigator Workspace IDE (`src/api/workspace.html`)  
**Audit Date**: 2026-09-07  
**Status**: 100% OPERATIONAL — ZERO DEAD CONTROLS  

---

### 1. Header & Navigation Controls

| UI Control | Selector / Element | Frontend Action | HTTP Request | Backend Endpoint | Data Source & Auth | Expected Result | Actual Result |
|---|---|---|---|---|---|---|---|
| **Brand Home** | `.brand-container` | Click brand logo/title | None | Internal Tab Switch | Client Router | Switch to Case Workspace (`view-cases`) | **VERIFIED** |
| **Tab: Case Workspace** | `#tab-btn-cases` | Click tab | None | Internal Tab Switch | Client Router | Activates Case Workspace, updates tab highlight | **VERIFIED** |
| **Tab: Evidence Explorer** | `#tab-btn-explorer` | Click tab | `GET` | `/api/v1/cases/{case_id}/artifacts` | SQLite Artifact DB (JWT) | Activates categorized explorer table | **VERIFIED** |
| **Tab: Crime Contact Network** | `#tab-btn-network` | Click tab | `GET` | `/api/v1/cases/{case_id}/graph?demo=false` | Kùzu Graph Engine (JWT) | Activates historical Cytoscape graph canvas & SVG rings | **VERIFIED** |
| **Case Selector Dropdown** | `#case-selector` | Change selection | `GET` | `/api/v1/cases`, `/api/v1/cases/{id}/evidence`, `/api/v1/cases/{id}/artifacts`, `/api/v1/cases/{id}/graph` | Case DB, Evidence DB, Artifact DB, Graph (JWT) | Updates case context, re-fetches all case-scoped resources | **VERIFIED** |
| **Sidebar Toggle** | `#btn-toggle-sidebar` | Click button | None | DOM class toggle | Client Layout Engine | Collapses / expands Left Explorer panel | **VERIFIED** |
| **Inspector Toggle** | `#btn-toggle-inspector` | Click button | None | DOM class toggle | Client Layout Engine | Collapses / expands Right Contextual Inspector panel | **VERIFIED** |
| **Console Toggle** | `#btn-toggle-console-btn` | Click button | None | DOM class toggle | Client Layout Engine | Collapses / expands Bottom Activity Console | **VERIFIED** |
| **Logout Button** | `.btn-header-logout` | Click button | None | Session Cleared | Client SessionStorage | Clears JWT token, presents login screen overlay | **VERIFIED** |

---

### 2. Left Case Explorer (Hierarchical Tree)

| UI Control | Selector / Element | Frontend Action | HTTP Request | Backend Endpoint | Data Source & Auth | Expected Result | Actual Result |
|---|---|---|---|---|---|---|---|
| **Case Root Node** | `#tree-node-case-root` | Click root node | None | Tab Switch | Client Router | Focuses active case details | **VERIFIED** |
| **Refresh Explorer** | `.explorer-header button` | Click refresh icon | `GET` | All case APIs | JWT Bearer | Reloads cases, evidence, artifacts, and graph | **VERIFIED** |
| **Evidence Branch Toggle** | `text=Evidence Artifacts` | Click branch | None | DOM toggle | Client Tree Engine | Expands/collapses evidence category sub-tree | **VERIFIED** |
| **Documents Branch** | `#tree-cat-documents` | Click category | `GET` | `/api/v1/cases/{id}/artifacts?category=DOCUMENT` | Artifact DB (JWT) | Expands document sub-items, filters explorer table | **VERIFIED** |
| **Document Sub-Item** | `#items-documents .tree-sub-item` (e.g. `Jeevan Setu.pdf`) | Click artifact | `GET` | `/api/v1/cases/{id}/artifacts/{id}/content`, `/api/v1/cases/{id}/artifacts/{id}/parsed` | Evidence Store & Parsed DB (JWT) | Opens embedded PDF viewer in center, populates right inspector | **VERIFIED** |
| **Images Branch** | `#tree-cat-images` | Click category | `GET` | `/api/v1/cases/{id}/artifacts?category=IMAGE` | Artifact DB (JWT) | Expands image sub-items, filters explorer table | **VERIFIED** |
| **Image Sub-Item** | `#items-images .tree-sub-item` (e.g. `Golden Temple Aarti.png`) | Click artifact | `GET` | `/api/v1/cases/{id}/artifacts/{id}/content`, `/api/v1/cases/{id}/artifacts/{id}/parsed` | Evidence Store & Parsed DB (JWT) | Opens embedded image viewer in center, populates right inspector | **VERIFIED** |
| **Databases Category** | `#tree-cat-databases` | Click category | `GET` | `/api/v1/cases/{id}/artifacts?category=DATABASE` | Artifact DB (JWT) | Filters table to databases | **VERIFIED** |
| **Spreadsheets Category** | `#tree-cat-spreadsheets` | Click category | `GET` | `/api/v1/cases/{id}/artifacts?category=SPREADSHEET` | Artifact DB (JWT) | Filters table to spreadsheets | **VERIFIED** |
| **Emails Category** | `#tree-cat-emails` | Click category | `GET` | `/api/v1/cases/{id}/artifacts?category=EMAIL` | Artifact DB (JWT) | Filters table to emails | **VERIFIED** |
| **CDR Category** | `#tree-cat-cdr` | Click category | `GET` | `/api/v1/cases/{id}/artifacts?category=CDR` | Artifact DB (JWT) | Filters table to CDRs | **VERIFIED** |
| **Logs Category** | `#tree-cat-logs` | Click category | `GET` | `/api/v1/cases/{id}/artifacts?category=LOG` | Artifact DB (JWT) | Filters table to logs | **VERIFIED** |
| **Recovered Category** | `#tree-cat-recovered` | Click category | `GET` | `/api/v1/cases/{id}/artifacts?category=RECOVERED` | Artifact DB (JWT) | Filters table to recovered files | **VERIFIED** |
| **Other Category** | `#tree-cat-other` | Click category | `GET` | `/api/v1/cases/{id}/artifacts?category=OTHER` | Artifact DB (JWT) | Filters table to other artifacts | **VERIFIED** |
| **Processing & Intake** | `#tree-node-processing` | Click node | None | Tab Switch | Client Router | Navigates to Case & Intake View | **VERIFIED** |
| **Reports Node** | `#tree-node-reports` | Click node | None | Tab Switch | Client Router | Navigates to Case Context & Reports View | **VERIFIED** |
| **Crime Contact Network Node** | `#tree-node-network` | Click node | `GET` | `/api/v1/cases/{id}/graph?demo=false` | Kùzu Graph Engine (JWT) | Opens historical Cytoscape graph canvas | **VERIFIED** |

---

### 3. Center Workspace — Case & Evidence Views

| UI Control | Selector / Element | Frontend Action | HTTP Request | Backend Endpoint | Data Source & Auth | Expected Result | Actual Result |
|---|---|---|---|---|---|---|---|
| **Add Evidence Button** | `text=Add Evidence` | Click button | None | Modal open | Client UI | Opens modal to register forensic container | **VERIFIED** |
| **Evidence Registration Submit** | `#modal-add-evidence form` | Submit form | `POST` | `/api/v1/cases/{id}/evidence` | Local image allowlist & SHA-256 (JWT) | Registers E01 container, discovers .E02, stores metadata | **VERIFIED** |
| **Verify Evidence Hash** | `text=Verify Hash` | Click button | `POST` | `/api/v1/cases/{id}/evidence/{id}/verify` | Evidence Store (JWT) | Audits 100% bit-for-bit SHA-256 match | **VERIFIED** |
| **Process E01 Button** | `text=Process E01` | Click button | `POST` | `/api/v1/cases/{id}/evidence/{id}/process` | E01 Engine Subprocess (JWT) | Queues isolated forensic worker job | **VERIFIED** |
| **Category Filter Buttons** | `.cat-btn` | Click filter | `GET` | `/api/v1/cases/{id}/artifacts?category=...` | Artifact DB (JWT) | Filters artifact table rows | **VERIFIED** |
| **Artifact Search Input** | `#explorer-search` | Type query | None | Live text filter | Client Filter | Filters artifacts by ID, filename, or SHA-256 | **VERIFIED** |
| **Open Artifact Action** | `text=Open` | Click button | `GET` | `/api/v1/cases/{id}/artifacts/{id}` | Artifact DB (JWT) | Opens integrated center viewer tab | **VERIFIED** |
| **Direct View Action** | `text=View` | Click button | `GET` | `/api/v1/cases/{id}/artifacts/{id}/content` | Streaming Binary Store (JWT) | Streams binary to embedded viewer | **VERIFIED** |
| **Back to Explorer** | `text=Back to Explorer` | Click button | None | Tab Switch | Client Router | Returns from viewer to table view | **VERIFIED** |

---

### 4. Center Workspace — Historical Crime Contact Network

| UI Control | Selector / Element | Frontend Action | HTTP Request | Backend Endpoint | Data Source & Auth | Expected Result | Actual Result |
|---|---|---|---|---|---|---|---|
| **Demo Mode Toggle** | `#btn-toggle-demo` | Click toggle | `GET` | `/api/v1/cases/{id}/graph?demo=true/false` | Dynamic Kùzu Query (JWT) | Switches between Real Case Data and Demo Mode | **VERIFIED** |
| **Target Search Input** | `#path-target-input` | Type query | None | Local/API lookup | Client Graph | Identifies target entity for shortest path | **VERIFIED** |
| **Network Spread Slider** | `#network-spread-slider` | Slide range | None | SVG re-render | Client SVG Engine | Dynamically rescales concentric rings and radar spokes | **VERIFIED** |
| **Reset Layout Button** | `text=Reset Layout` | Click button | None | Cytoscape layout | Cytoscape Concentric | Re-runs concentric layout with anchor centered | **VERIFIED** |
| **Find Shortest Path Button** | `text=Find Shortest Path` | Click button | `GET` | `/api/v1/cases/{id}/graph/shortest_path` | Graph Dijkstra BFS (JWT) | Calculates shortest path hops between anchor & target | **VERIFIED** |
| **Explore 1-Hop Neighbors** | `text=Explore 1-Hop Neighbors` | Click button | `GET` | `/api/v1/cases/{id}/graph/neighbors/{id}` | Graph 1-hop Query (JWT) | Lists directly connected 1-hop associates | **VERIFIED** |
| **Layer 1 Filter Button** | `#btn-filter-l1` | Click button | None | Cytoscape class toggle | Client Canvas | Highlights Layer 1 (Direct Associates), dims others | **VERIFIED** |
| **Layer 2 Filter Button** | `#btn-filter-l2` | Click button | None | Cytoscape class toggle | Client Canvas | Highlights Layer 2 (Broader Network), dims others | **VERIFIED** |
| **Layer 3 Filter Button** | `#btn-filter-l3` | Click button | None | Cytoscape class toggle | Client Canvas | Highlights Layer 3 (Extended Network), dims others | **VERIFIED** |
| **Show All Filter Button** | `#btn-filter-all` | Click button | None | Cytoscape class toggle | Client Canvas | Restores full visibility to all layers | **VERIFIED** |
| **Fit Graph Button** | `text=Fit Graph` | Click button | None | Cytoscape animate | Cytoscape Engine | Fits entire graph smoothly inside viewport | **VERIFIED** |
| **Cytoscape Node Tap** | `cy.on('tap', 'node')` | Tap person node | `GET` | `/api/v1/cases/{id}/graph/entity/{id}` | Kùzu Entity Table (JWT) | Highlights neighborhood, populates Lead Inspector | **VERIFIED** |
| **Cytoscape Edge Tap** | `cy.on('tap', 'edge')` | Tap edge | `GET` | `/api/v1/cases/{id}/graph/relationship/{id}` | Kùzu Edge Table (JWT) | Highlights edge & nodes, populates Relationship Inspector | **VERIFIED** |
| **Cytoscape Canvas Drag** | `cy.on('drag', 'node')` | Drag node | None | Clamping Math | Layer Boundary Limiter | Clamps node position within assigned layer bounds | **VERIFIED** |

---

### 5. Right Contextual Inspector

| UI Control | Selector / Element | Frontend Action | HTTP Request | Backend Endpoint | Data Source & Auth | Expected Result | Actual Result |
|---|---|---|---|---|---|---|---|
| **Run Deep Parsing** | `#btn-deep-parse-action` | Click button | `POST` | `/api/v1/cases/{id}/artifacts/{id}/parse?force=true` | Slice 8A Parsers (JWT) | Parses format (PDF/Image/SQLite), renders observations | **VERIFIED** |
| **Human Review Decision** | `text=Review` | Click button | `POST` | `/api/v1/cases/{id}/graph/verify` | Verification Store & Audit (JWT) | Records status decision `UNDER_REVIEW` | **VERIFIED** |
| **Human Verify Lead** | `text=Verify` | Click button | `POST` | `/api/v1/cases/{id}/graph/verify` | Verification Store & Audit (JWT) | Records status decision `HUMAN_VERIFIED_LEAD` | **VERIFIED** |
| **Human Reject Lead** | `text=Reject` | Click button | `POST` | `/api/v1/cases/{id}/graph/verify` | Verification Store & Audit (JWT) | Records status decision `REJECTED_ASSOCIATION` | **VERIFIED** |

---

### 6. Bottom Activity / Terminal Console

| UI Control | Selector / Element | Frontend Action | HTTP Request | Backend Endpoint | Data Source & Auth | Expected Result | Actual Result |
|---|---|---|---|---|---|---|---|
| **Console Header Bar** | `.console-header` | Click bar | None | CSS height transition | Client Layout Engine | Expands/collapses console between 26px and 160px | **VERIFIED** |
| **Clear Console** | `text=Clear Console` | Click button | None | Clear DOM children | Client Logging Engine | Clears log entries, resets event counter | **VERIFIED** |
| **Event Stream Auto-scroll** | `#console-log-body` | Event trigger | None | Append DOM entry | Client Event Bus | Appends timestamped log with color badge, scrolls to bottom | **VERIFIED** |
