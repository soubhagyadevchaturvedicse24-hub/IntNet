# Benchmark Specification: Sigma.js vs Cytoscape.js (Investigator Graph UI)

**Document Version:** 1.0.0  
**Status:** `[PROPOSED / OPEN]` (Benchmark Specification)  
**Date:** 2026-09-05  
**Candidate Technologies:** **Cytoscape.js** vs **Sigma.js**  

---

## 1. Objective
To evaluate whether **Cytoscape.js** (Canvas/DOM) or **Sigma.js** (WebGL/Graphology) provides the optimal combination of rendering performance, parametric concentric ring layouts, and interactive inspector UX for the CRIMENET Investigator Dashboard.

---

## 2. Hypothesis
* *Hypothesis 1:* Cytoscape.js provides superior out-of-the-box support for parameterized concentric layouts (Red $\rightarrow$ Yellow $\rightarrow$ Green rings based on CCC scores) and edge/node click events on subgraphs up to 3,000 nodes.
* *Hypothesis 2:* Sigma.js provides smoother WebGL rendering at high node counts ($>5,000$ nodes), but requires substantially higher development effort to implement custom concentric coordinate geometry and evidence inspector overlays.

---

## 3. Dataset / Fixture
* Synthetic crime subgraphs exported from the graph database generator:
  * **Scale S (Small):** 200 nodes, 500 edges (typical single-suspect immediate cluster).
  * **Scale M (Medium):** 1,500 nodes, 4,000 edges (multi-suspect syndicate ring).
  * **Scale L (Large):** 5,000 nodes, 15,000 edges (multi-case macro network).
  * **Scale XL (Stress):** 10,000 nodes, 30,000 edges (unfiltered case universe).

---

## 4. Environment
* **Frontend Runtime:** React 18+ / TypeScript / Vite.
* **Browser Baseline:** Chromium (Chrome 125+) and Firefox on Windows 11.
* **Display Resolution:** $1920 \times 1080$ @ 60 Hz.
* **Host Hardware:** Intel i7 / 16 GB RAM / Integrated or Dedicated GPU.

---

## 5. Procedure
1. **Initial Mount & Render Test:**
   * Load Scale S, M, L, XL graph JSON fixtures into Cytoscape.js and Sigma.js canvas containers.
   * Measure Initial Render Time (ms from JSON parse to first frame paint).
2. **Concentric Ring Layout Calculation Test:**
   * Execute concentric layout algorithm assigning nodes to Red, Yellow, Green zones based on an explicit node property (`ccc_score`).
   * Measure layout calculation duration and animation smoothness.
3. **Interaction & Event Dispatch Benchmark:**
   * Programmatically trigger 100 node click and edge click events.
   * Measure latency from click event to inspector sidebar render with evidence metadata.
4. **Pan / Zoom FPS Measurement:**
   * Execute automated 10-second pan and zoom stress loop; record average FPS and frame drop count via `requestAnimationFrame` performance observer.
5. **Memory & Bundle Footprint:**
   * Measure JS heap allocation in browser DevTools and production bundle size (minified + gzipped).

---

## 6. Metrics (Mapped to Methodology)
* **Performance:** Initial render latency (ms), layout execution time (ms), Pan/Zoom FPS (P50, min FPS).
* **Resource Usage:** Browser JS heap memory (MB).
* **Integration Effort:** Lines of code required to implement concentric ring layout + inspector click handlers.
* **Maintainability & Ergonomics:** TypeScript typing quality, documentation, React wrapper stability.

---

## 7. Repetitions
* 10 automated test runs per graph scale size with fresh browser tab context.

---

## 8. Expected Output
* UI benchmark report (`BENCHMARKS/reports/graph_visualization_benchmark.json`).
* Visual capture comparison of layout quality across both libraries.

---

## 9. Acceptance Criteria
* **Render Speed (Scale M - 1.5k nodes):** Initial render $< 300\text{ ms}$.
* **Frame Rate (Scale M):** Steady $\ge 50\text{ FPS}$ during continuous pan/zoom.
* **Inspector Responsiveness:** Click-to-panel render latency $< 50\text{ ms}$.
* **Concentric Layout Accuracy:** Exact visual segregation into concentric circles based on mathematical score thresholds.

---

## 10. Threats to Validity
* WebGL GPU acceleration differences across host machines (integrated vs dedicated GPU).
* Canvas vs WebGL rendering differences in text/label legibility.

---

## 11. What Result Would Change the Architectural Decision
* **Select Sigma.js if:** Cytoscape.js suffers unacceptable frame drops ($< 25\text{ FPS}$) on standard syndicate cluster sizes ($1,000 - 3,000$ nodes), and custom concentric layout in Graphology is straightforward to maintain.
* **Retain Cytoscape.js if:** Cytoscape.js maintains smooth performance ($> 50\text{ FPS}$) on typical suspect cluster sizes ($< 3,000$ nodes) while providing vastly simpler concentric ring configuration and inspector event integration.
