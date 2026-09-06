# ADR-005: Investigator Graph Visualization Engine

* **Status:** `[PROPOSED / OPEN]`  
* **Date:** 2026-09-05  
* **Decision Makers:** CRIMENET Engineering Team  

---

## 1. Context and Problem Statement
The investigator dashboard requires an interactive graph canvas that renders suspect clusters in a parameterized concentric ring layout (Red $\rightarrow$ Yellow $\rightarrow$ Green zones based on CCC scores) with instant edge-click inspector access.

---

## 2. Decision Drivers
* Parametric concentric ring layout calculation based on node properties.
* Interactive responsiveness (pan, zoom, node/edge click handlers).
* Performance on standard suspect cluster sizes ($500 - 3,000$ active nodes).
* Lightweight bundle size and TypeScript ecosystem integration.

---

## 3. Considered Options
* **Option A:** Cytoscape.js (Canvas/DOM with native concentric layout).
* **Option B:** Sigma.js (WebGL with Graphology).
* **Option C:** D3.js (SVG/Canvas with custom force simulation).

---

## 4. Current Status
* **Status:** `[PROPOSED / OPEN]` — Phase 4 Investigator Graph Intelligence UI integrated using **Cytoscape.js** for prototype graph rendering, node selection, edge inspection, and evidence traceability panels.

---

## 5. Phase 4 Implementation & Verification Results
* **Integrated Canvas:** Cytoscape.js (COSE layout + custom node color coding by entity type).
* **Interactive Capabilities:**
  * Node Tap $\rightarrow$ Emits `/api/entity/{id}` request $\rightarrow$ Populates Entity Inspector Panel.
  * Edge Tap $\rightarrow$ Emits `/api/relationship/{id}` request $\rightarrow$ Answers *"Why does this link exist?"* with full evidence contract metadata.
  * Search Bar & Reset $\rightarrow$ 1-Hop / 2-Hop neighborhood queries.
* **Responsible AI Compliance:** Enforces investigator decision-support terminology (*Analytical Lead*, *Indicator*, *Potential Association*, *Confidence*, *Human Verification*). Zero automated criminal labels assigned.
* **Status:** Maintained as `[PROPOSED / OPEN]` pending comparative benchmark against WebGL-based engines (Sigma.js) for large-scale graphs (>10k nodes).

