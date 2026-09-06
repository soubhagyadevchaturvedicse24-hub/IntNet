# CRIMENET Intelligence Lab — Project Status

**Last Updated:** 2026-09-06  
**Document Classification Standard:**
- **[BASELINE]** — Confirmed project requirement or core principle.
- **[DECISION]** — Explicitly accepted architectural choice.
- **[PROPOSAL]** — Recommended approach, subject to design review and validation.
- **[UNKNOWN]** — Requires technical investigation or environment verification.
- **[EXPERIMENTAL]** — Requires testing, comparative benchmarking, or empirical data.

**Technology Radar Evaluation Standard:**
- **`KEEP`** — Validated by evidence and retained as the optimal choice.
- **`BENCHMARK`** — Requires empirical testing/benchmarking against competitors.
- **`REPLACE`** — Evidence demonstrates an alternative is superior for our constraints.
- **`INVESTIGATE`** — Potential candidate requiring deeper technical discovery.
- **`REJECT`** — Disqualified due to licensing, performance, or operational mismatch.

---

## 1. Current Project Phase

**Phase:** `LAYERED INTERACTIVE NETWORK + SAFE RADIAL BAND DRAGGING + INTERACTIVE LAYER FILTERS + 100% BACKEND DATA VALIDATED`  
**Focus:** 
- **Layered Interactive Network:** 100% dynamic concentric layer calculation using BFS distance from selected subject (Layer 0 = Subject, Layer 1 = Direct Contacts, Layer 2 = Distance 2 Contacts, Layer 3 = Distance 3 Contacts). Zero hardcoded illustrative constants.
- **Atmospheric Glowing Background Layers:** SVG concentric layers synchronized on pan/zoom (`syncSvgTransform()`) with `#glow-red` (Inner Layer 1), `#glow-yellow` (Middle Layer 2), and `#glow-green` (Outer Layer 3), plus `#centerRedGlow` reticle behind primary subject.
- **Safe Radial Band Dragging:** Associated nodes are draggable and dynamically constrained to their assigned analytical layer band via polar clamping (`layerBounds`: L1 $[110, 220]$, L2 $[225, 360]$, L3 $[365, 520]$ px) without snapping back or colliding with the primary subject.
- **Central Subject Fixed at True Center:** `CAN-PER-0001` (Vikram Singh) locked at canvas center with avatar icon, core radial glow, reticle, and directional connector arrows to Layer 1.
- **Interactive Layer Filters:** Right panel filters `[🔴 Layer 1]`, `[🟡 Layer 2]`, `[🟢 Layer 3]`, and `[👁 Show All]` smoothly focus the selected layer (opacity 1.0) and dim others (opacity 0.12) non-destructively.
- **Information Architecture:** Collapsible accordion sections across left and right panels, floating bottom-right dock containing Analytical Layers Legend and Network Minimap with zoom/fit/compass controls.
- **Backend & Verification:** Live on `http://127.0.0.1:8000`. All 15 unit tests pass (`python -m pytest tests/`), and automated integration verification (`scratch/test_verification.py`) confirms all endpoints and mutations succeed.

---

## 2. Confirmed Baseline [BASELINE]

* **System Purpose & Role:**
  * AI-assisted decision-support system for investigators to discover leads, indicators, potential associations, and supporting evidence.
  * **Strict Boundary:** The system does **not** determine guilt or label individuals as "guilty" or "criminal".
  * Standard terminology: *Lead, Indicator, Potential Association, Confidence, Analytical Insight, Supporting Evidence, Human Verification*.
* **Forensic Decoupling:**
  * Autopsy is strictly an *Observation / Examination Engine*, not the product itself.
  * Direct dependency on undocumented Autopsy internal databases is prohibited.
  * An intermediate *Normalized Evidence Contract* must insulate the Processing and Dashboard layers.
  * Complete provenance must be maintained from raw image $\rightarrow$ extracted artifact $\rightarrow$ derived intelligence $\rightarrow$ graph edge.
* **Asynchronous Operation:**
  * Forensic analysis and extraction are non-instantaneous; ingest must be asynchronous with explicit job states (*Uploaded*, *Queued*, *Processing*, *Extracting*, *Normalizing*, *Ready*, *Failed*).
* **Synthetic-First Demonstration:**
  * Prototype evaluation and demonstration rely exclusively on controlled synthetic datasets (synthetic FIR records, photos, communications, and forensic images). No unverified access to confidential NCRB data is assumed.
* **Evidence-Backed Progress Principle:**
  * *"Build less. Discover more. Validate everything. Build only what matters."*
  * No component is declared finalized without empirical benchmark evidence and documented ADRs.

---

## 3. Current Architecture & Technology Candidates

```text
+-------------------------------------------------------------------------+
|                         FORENSIC EVIDENCE                               |
|                  (Synthetic Forensic Image: E01 / RAW)                  |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|              OBSERVATION ENGINE [CANDIDATE / INVESTIGATE]               |
|                       (Primary Candidate: Autopsy)                      |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|               NORMALIZED EVIDENCE CONTRACT [PROPOSAL]                   |
|       (Decoupled JSON Schema: Provenance, Artifacts, Metadata)          |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                     PROCESSING LAYER [PROPOSAL]                         |
|   - Modular Facial Recognition (Model-Agnostic Interface) [BENCHMARK]   |
|   - Critical Contact & Association Scoring (CCC) [PROPOSAL]             |
|   - Entity Resolution & Graph Builder [PROPOSAL]                        |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                 GRAPH DATABASE [CANDIDATES / BENCHMARK]                 |
|              (Candidates: Memgraph vs FalkorDB vs Neo4j)                |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                BACKEND API [CANDIDATE / INVESTIGATE]                    |
|                        (Candidate: FastAPI)                             |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|             INVESTIGATOR DASHBOARD [CANDIDATES / INVESTIGATE]           |
|       - UI Framework: React + TypeScript [INVESTIGATE]                  |
|       - Graph Visualizer: Cytoscape.js [INVESTIGATE]                    |
|       - Explainable "Why Linked?" Provenance Inspector [BASELINE]       |
|       - Human Verification Action Panel [BASELINE]                      |
+-------------------------------------------------------------------------+
```

---

## 4. Open Decisions & Candidate Radar (Evaluated in `RESEARCH/TECHNOLOGY_RADAR_REVIEW.md`)

| # | Layer / Component | Candidates Evaluated | Radar Status | Evaluation Spec / ADR Reference |
|---|---|---|---|---|
| 1 | **Graph Database Engine** | Memgraph vs Neo4j vs FalkorDB (Kùzu / NetworkX) | `BENCHMARK COMPLETED (PROTOTYPE RECOMMENDED)` | Executed 21.5k node / 40k edge workload. Report: [`BENCHMARKS/reports/graph_db_benchmark_results.json`](file:///D:/Proto%20SIH/BENCHMARKS/reports/graph_db_benchmark_results.json) \| ADR: `DECISIONS/ADR-004-graph-database.md` (`[PROPOSED / OPEN]`) |
| 2 | **Forensic Observation** | Autopsy vs IPED | `VERTICAL SLICE VALIDATED` | Executed real RAW image vertical slice. Report: [`BENCHMARKS/reports/phase1_autopsy_vs_iped_report.json`](file:///D:/Proto%20SIH/BENCHMARKS/reports/phase1_autopsy_vs_iped_report.json) \| ADR: `DECISIONS/ADR-002-observation-engine.md` (`[PROPOSED / OPEN]`) |
| 3 | **Entity Resolution** | Rule-Based Normalizer vs Splink | `VERTICAL SLICE VALIDATED` | Executed 15-observation test slice (F1=1.0). Report: [`BENCHMARKS/reports/entity_resolution_eval_report.json`](file:///D:/Proto%20SIH/BENCHMARKS/reports/entity_resolution_eval_report.json) \| ADR: `DECISIONS/ADR-007-entity-resolution.md` (`[PROPOSED / OPEN]`) |
| 4 | **Facial Recognition** | In-Process Modular Interface vs CompreFace | `BENCHMARK` | Spec: `BENCHMARKS/BENCHMARK_SPEC_INSIGHTFACE_VS_COMPREFACE.md` \| ADR: `DECISIONS/ADR-006-face-model.md` (`[PROPOSED / OPEN]`) |
| 5 | **Graph Visualization** | Cytoscape.js vs Sigma.js | `PROTOTYPE INTEGRATED` | Integrated Cytoscape.js single-page visualizer with FastAPI evidence inspector panel. ADR: `DECISIONS/ADR-005-graph-visualization.md` (`[PROPOSED / OPEN]`) |
| 6 | **Backend API** | FastAPI | `KEEP` | Base: `ARCHITECTURE.md` \| ADR: `DECISIONS/ADR-001-product-platform.md` (`[PROPOSED / OPEN]`) |
| 7 | **Frontend Framework** | React + TypeScript | `KEEP` | Base: `ARCHITECTURE.md` \| ADR: `DECISIONS/ADR-001-product-platform.md` (`[PROPOSED / OPEN]`) |
| 8 | **Critical Contact / CCC Scoring** | Deterministic 4-Factor Weighted Model | `FORMULATION VALIDATED` | Implemented in `src/analytics/ccc_scorer.py`. Report: [`BENCHMARKS/reports/ccc_scoring_eval_report.json`](file:///D:/Proto%20SIH/BENCHMARKS/reports/ccc_scoring_eval_report.json) \| ADR: `DECISIONS/ADR-008-ccc-scoring.md` (`[PROPOSED / OPEN]`) |
| 9 | **Evidence Contract Schema (v1)** | `EvidenceContract_v1` JSON Schema | `PROPOSAL` | Spec: `RESEARCH/EVIDENCE_CONTRACT_V1.md` \| ADR: `DECISIONS/ADR-003-evidence-contract.md` (`[PROPOSED / OPEN]`) |

---

## 5. Repository Structure & Artifact Index

* **Core Architecture:** [`ARCHITECTURE.md`](file:///D:/Proto%20SIH/ARCHITECTURE.md)
* **Evaluation Methodology:** [`RESEARCH/TECHNOLOGY_BENCHMARK_METHODOLOGY.md`](file:///D:/Proto%20SIH/RESEARCH/TECHNOLOGY_BENCHMARK_METHODOLOGY.md)
* **Evidence Contract:** [`RESEARCH/EVIDENCE_CONTRACT_V1.md`](file:///D:/Proto%20SIH/RESEARCH/EVIDENCE_CONTRACT_V1.md)
* **Technology Radar Review:** [`RESEARCH/TECHNOLOGY_RADAR_REVIEW.md`](file:///D:/Proto%20SIH/RESEARCH/TECHNOLOGY_RADAR_REVIEW.md)
* **Benchmark Specifications:**
  * [`BENCHMARKS/BENCHMARK_SPEC_AUTOPSY_VS_IPED.md`](file:///D:/Proto%20SIH/BENCHMARKS/BENCHMARK_SPEC_AUTOPSY_VS_IPED.md)
  * [`BENCHMARKS/BENCHMARK_SPEC_MEMGRAPH_VS_NEO4J.md`](file:///D:/Proto%20SIH/BENCHMARKS/BENCHMARK_SPEC_MEMGRAPH_VS_NEO4J.md)
  * [`BENCHMARKS/BENCHMARK_SPEC_SIGMA_VS_CYTOSCAPE.md`](file:///D:/Proto%20SIH/BENCHMARKS/BENCHMARK_SPEC_SIGMA_VS_CYTOSCAPE.md)
  * [`BENCHMARKS/BENCHMARK_SPEC_INSIGHTFACE_VS_COMPREFACE.md`](file:///D:/Proto%20SIH/BENCHMARKS/BENCHMARK_SPEC_INSIGHTFACE_VS_COMPREFACE.md)
* **Phase 1 Benchmark Execution Artifacts (Autopsy vs IPED):**
  * Ground-Truth Manifest Spec: [`RESEARCH/SYNTHETIC_FORENSIC_GROUND_TRUTH.md`](file:///D:/Proto%20SIH/RESEARCH/SYNTHETIC_FORENSIC_GROUND_TRUTH.md)
  * Observation Adapter Spec: [`RESEARCH/OBSERVATION_ADAPTER_SPEC.md`](file:///D:/Proto%20SIH/RESEARCH/OBSERVATION_ADAPTER_SPEC.md)
  * Phase 1 Execution Plan: [`BENCHMARKS/PHASE_1_AUTOPSY_VS_IPED_PLAN.md`](file:///D:/Proto%20SIH/BENCHMARKS/PHASE_1_AUTOPSY_VS_IPED_PLAN.md)
  * Executed Benchmark Report: [`BENCHMARKS/reports/phase1_autopsy_vs_iped_report.json`](file:///D:/Proto%20SIH/BENCHMARKS/reports/phase1_autopsy_vs_iped_report.json)
* **Architectural Decision Records (`DECISIONS/` & `docs/adr/`):**
  * `DECISIONS/ADR-001-product-platform.md` (`[PROPOSED / OPEN]`)
  * `DECISIONS/ADR-002-observation-engine.md` (`[PROPOSED / OPEN]`)
  * `DECISIONS/ADR-003-evidence-contract.md` (`[PROPOSED / OPEN]`)
  * `DECISIONS/ADR-004-graph-database.md` (`[PROPOSED / OPEN]`)
  * `DECISIONS/ADR-005-graph-visualization.md` (`[PROPOSED / OPEN]`)
  * `DECISIONS/ADR-006-face-model.md` (`[PROPOSED / OPEN]`)
  * `DECISIONS/ADR-007-entity-resolution.md` (`[PROPOSED / OPEN]`)

---

## 6. Unknowns & Technical Questions [UNKNOWN]

* **Autopsy vs IPED Headless Parity:** Verifying whether IPED or Autopsy extracts full SQLite communication databases headlessly with higher fidelity.
* **Byte Offset & Carved Path Consistency:** Consistency of `tsk_file_layout.byte_start` and relative disk paths for carved media across different Autopsy ingest module versions.
* **Synthetic Graph Dataset Generation:** Availability of realistic relational generators for synthetic FIRs, CDRs (Call Detail Records), and location timelines.
* **Target Compute Constraints:** Minimum hardware baseline for running local FastAPI + Graph DB + Model Ingest simultaneously without performance degradation.

---

## 7. Project Risks & Mitigations

* **Risk: Premature Technology Lock-in**
  * *Impact:* High architectural friction if an untested database or model fails under real loads.
  * *Mitigation:* Strict interface abstraction layers for graph storage and face embeddings until benchmark ADRs are finalized.
* **Risk: Tight Coupling to Autopsy Database Internals**
  * *Impact:* Loss of modularity; breakage across Autopsy versions.
  * *Mitigation:* Ingest layer must strictly emit the Normalized Evidence Contract v1; downstream analytics never connect directly to Autopsy SQLite/PostgreSQL schemas.
* **Risk: UI Blocked by Long-Running Forensic Tasks**
  * *Impact:* Poor investigator user experience and connection timeouts.
  * *Mitigation:* Asynchronous job queue with real-time status reporting and polling/WebSocket notifications.
* **Risk: Black-Box Scoring Output**
  * *Impact:* Lack of investigator trust; inadmissible/unhelpful analysis.
  * *Mitigation:* Mandatory "Why Linked?" evidence provenance panel on every graph edge and entity.

---

## 8. First Vertical Slice Scope

The primary milestone is proving the architecture end-to-end with the smallest viable path:

1. **Upload / Select** a synthetic forensic image (or pre-extracted synthetic image directory).
2. **Execute Ingest / Observation** via Autopsy or IPED (or normalized mock for unit validation).
3. **Emit** Normalized Evidence Contract v1.
4. **Run Processing**: Extract synthetic photo $\rightarrow$ Run facial embedding $\rightarrow$ Match against synthetic FIR records.
5. **Construct Graph**: Ingest matched entities and relationships into the prototype graph engine.
6. **Render Investigator UI**: Display central target with concentric ring scoring via Cytoscape.js.
7. **Explain Link**: Investigator clicks an edge $\rightarrow$ Inspects "Why Are They Linked?" panel showing source photograph, similarity score, and FIR reference.
8. **Human Verification**: Investigator logs verification status.

---

## 9. Immediate Next Actions

1. `[PROPOSAL]` **Critical Contact / CCC Scoring Formalization:** Formulate the mathematical scoring rules, weights, and ring placement logic (`RESEARCH/CCC_SCORING_FORMULATION.md`).
2. `[EXPERIMENTAL]` **Synthetic Graph Dataset Generator Design:** Create the deterministic generation script (`scripts/generate_synthetic_graph.py`) producing the 21.5k node / 40k edge dataset fixture.
3. `[EXPERIMENTAL]` **Automated Benchmark Harness Setup:** Build the Docker-based benchmark execution harnesses for Graph DB, Observation, Visualization, and Face Recognition layers.
