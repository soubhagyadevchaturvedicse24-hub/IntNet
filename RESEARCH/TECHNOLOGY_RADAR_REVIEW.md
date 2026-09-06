# Technology Radar Review & Candidate Evaluation

**Document Version:** 1.0.0  
**Date:** 2026-09-05  
**Context:** Critical evaluation of external Technology Radar recommendations (via NotebookLM) against the CRIMENET baseline architecture and engineering constraints.  
**Core Principle:** All radar proposals are treated as candidate hypotheses, not final decisions. No technology is selected or eliminated based on marketing claims or unverified assumptions.

---

## 1. Evaluation Classification Standard

Every proposed technology candidate is classified under one of five rigorous states:

* **`KEEP`** — Formally validated by evidence and retained as the active architectural standard.
* **`BENCHMARK`** — Requires empirical, head-to-head performance testing against competitors under identical conditions.
* **`REPLACE`** — Rigorous evidence proves an alternative is strictly superior for our specific constraints.
* **`INVESTIGATE`** — Promising candidate requiring deeper technical discovery, license verification, or prototype validation.
* **`REJECT`** — Formally disqualified due to licensing incompatibility, prohibitive resource overhead, or functional mismatch.

---

## 2. Comprehensive Candidate Evaluation Matrix

| Capability / Layer | Candidate Technology | Claim Type | Evidence / Primary Source | Strength | Unknowns & Operational Risks | Benchmark / Test Needed | Current Classification |
|---|---|---|---|---|---|---|---|
| **Forensic Observation** | **Autopsy** | Baseline Standard | SleuthKit Official Docs (`autopsy64.exe --runFromCommandLine=true`) | Mature DFIR ecosystem, native E01/RAW support, SQLite `autopsy.db` & CASE-UCO JSON export. | GUI launches during CLI run on Windows; completion signaling requires filesystem monitoring. | Measure batch ingest latency & artifact coverage against synthetic images. | **`INVESTIGATE`** *(Primary Candidate)* |
| **Forensic Observation** | **IPED** | Proposal / External Claim | IPED GitHub / Brazilian Federal Police Docs | CLI-first architecture, multi-threaded batch indexing, Lucene search, JSON/CSV exports. | Setup complexity, Java dependencies, config tuning for specific photo/EXIF extraction. | Head-to-head ingest speed & artifact extraction parity vs Autopsy. | **`INVESTIGATE`** *(Secondary Candidate)* |
| **DFIR Orchestration** | **OpenRelik** | Proposal / External Claim | Google OpenRelik GitHub (Apache 2.0) | Clean microservice workflow orchestration for multiple DFIR tools. | Prohibitive local overhead (Docker, Celery, Redis) for a local single-user prototype. | Evaluate minimum container footprint vs standalone Python subprocesses. | **`INVESTIGATE`** *(Deferred to Future Scale)* |
| **Entity Resolution** | **Splink** | Proposal / External Claim | Splink GitHub / UK Ministry of Justice (MIT) | Fast probabilistic record linkage (Fellegi-Sunter), DuckDB backend, zero infrastructure. | Parameter tuning complexity on Indian crime data schemas; integration into Evidence Contract. | Accuracy & throughput vs rule-based exact/Levenshtein matching on 20k records. | **`INVESTIGATE`** *(High Priority Candidate)* |
| **Facial Recognition** | **In-Process Model-Agnostic Interface** | Baseline Proposal | Standard Python ML Architecture (`FaceEmbeddingService`) | Zero extra server infrastructure, swappable models (InsightFace/ArcFace/FaceNet), full control. | CPU inference latency per image on non-GPU host machines. | Benchmark ROC-AUC, latency, and RAM across candidate model weights. | **`BENCHMARK`** *(Primary Candidate)* |
| **Facial Recognition** | **CompreFace** | Proposal / External Claim | Exadel CompreFace GitHub (Apache 2.0) | Turnkey REST API, pre-built face gallery management, web UI. | Heavy multi-container deployment (PostgreSQL, Redis, UI, API); redundant DB layer. | REST API latency & memory consumption vs direct in-process Python embeddings. | **`INVESTIGATE`** *(Do Not Replace In-Process Yet)* |
| **Graph Database** | **Memgraph** | Benchmark Candidate | Memgraph Docs (BSL 1.1 / MAGE Apache 2.0) | High-throughput in-memory C++ engine, OpenCypher support, native MAGE analytics. | RAM footprint under large workloads; BSL license conditions for offline distributions. | Full synthetic crime workload benchmark (21k nodes, 40k edges). | **`BENCHMARK`** |
| **Graph Database** | **FalkorDB** | Benchmark Candidate | FalkorDB GitHub / Docs (SSPL v1.0 / Custom) | GraphBLAS sparse matrix linear algebra, low memory, hybrid graph+vector capabilities. | SSPL license restrictions; driver maturity compared to Neo4j. | 1–3 hop traversals, memory footprint, and license compliance review. | **`INVESTIGATE`** *(Retained for Benchmark)* |
| **Graph Database** | **Neo4j** | Benchmark Candidate | Neo4j Docs (GPL v3 Community / Commercial) | Mature industry standard, rich Cypher tooling, Graph Data Science (GDS) library. | JVM startup latency and higher idle RAM consumption in local container. | Full synthetic crime workload benchmark (21k nodes, 40k edges). | **`BENCHMARK`** |
| **Graph Visualization** | **Cytoscape.js** | Baseline Proposal | Cytoscape.js Official Docs (MIT) | Native concentric layout algorithm (critical for Red/Yellow/Green rings), rich edge event API. | Performance degradation on $>10,000$ simultaneous unclustered nodes. | Frame rate & layout calculation time on 1k–5k entity graphs. | **`INVESTIGATE`** *(Primary Candidate)* |
| **Graph Visualization** | **Sigma.js** | Proposal / External Claim | Sigma.js / Graphology Docs (MIT) | WebGL-accelerated rendering capable of displaying 50k+ nodes smoothly. | Concentric ring placement requires custom coordinate math; fewer inspector interaction helpers. | Implementation complexity of concentric ring layouts vs Cytoscape.js. | **`INVESTIGATE`** *(Evaluate Only if WebGL is Required)* |
| **Backend API** | **FastAPI** | Baseline Decision | FastAPI Docs (MIT) | Native async support, high performance, automatic OpenAPI documentation, Python ML parity. | Worker thread management during heavy synchronous CPU tasks. | Verify async job queue latency during mock Autopsy ingestion. | **`KEEP`** |
| **Frontend UI** | **React + TypeScript** | Baseline Decision | React / TypeScript Standard (MIT) | Component modularity, strong typing, mature ecosystem for forensic inspector panels. | State synchronization with complex graph canvases. | Validate Cytoscape.js React wrapper component reactivity. | **`KEEP`** |

---

## 3. Deep-Dive Analysis on Critical Radar Claims

### A. Forensic Observation Layer: Autopsy vs IPED vs OpenRelik
* **Radar Hypothesis:** *"IPED should replace Autopsy because it is headless and faster."*
* **Verification & Evidence:**
  * IPED is an open-source Java tool (GPL v3) created by the Brazilian Federal Police. It is indeed CLI-first and highly efficient for batch indexing.
  * However, Autopsy's ecosystem is more mature for general DFIR, provides verified CASE-UCO export, and is already documented in our verification plan.
  * **Conclusion:** Do **NOT** replace Autopsy with IPED. Keep Autopsy as the primary observation candidate and treat IPED as an alternative candidate to be evaluated in a head-to-head ingest test. OpenRelik is too resource-heavy for a single-node prototype and is deferred.

---

### B. Entity Resolution: Custom Rule Engine vs Splink
* **Radar Hypothesis:** *"Splink provides probabilistic entity resolution out of the box."*
* **Verification & Evidence:**
  * Splink (MIT license) is an industry-standard library developed by the UK Ministry of Justice implementing the Fellegi-Sunter probabilistic record linkage framework.
  * It runs embedded on DuckDB with zero server overhead and handles fuzzy name matches, phonetic similarities, and typographical errors in phone numbers and addresses.
  * **Conclusion:** Classify Splink as **`INVESTIGATE`** (High Priority). It directly fits our Processing Layer entity resolution requirement without introducing heavy ML infrastructure.

---

### C. Facial Recognition: In-Process Modular Interface vs CompreFace
* **Radar Hypothesis:** *"CompreFace should be used as a standalone face recognition microservice."*
* **Verification & Evidence:**
  * CompreFace is an Exadel open-source project (Apache 2.0) that packages InsightFace/FaceNet behind a REST API and PostgreSQL database.
  * Running CompreFace introduces 3–4 additional Docker containers (PostgreSQL, CompreFace core, UI, Redis), adds HTTP serialization overhead, and duplicates entity storage.
  * A model-agnostic Python interface running in-process (e.g. `InsightFace` / `ArcFace` wrapped in `FaceEmbeddingService`) achieves identical accuracy with zero architectural bloat.
  * **Conclusion:** Do **NOT** adopt CompreFace. Retain the **Model-Agnostic Interface (`[BENCHMARK]`)** as the primary architecture; keep CompreFace as **`INVESTIGATE`** only for reference.

---

### D. Graph Database Selection: Memgraph vs FalkorDB vs Neo4j
* **Radar Hypothesis:** *"Memgraph is strictly better than Neo4j; FalkorDB should be eliminated due to licensing."*
* **Verification & Evidence:**
  * **FalkorDB Licensing:** FalkorDB uses the Server Side Public License (SSPL) / source-available terms. While SSPL restricts offering FalkorDB as a managed cloud service, it does not prevent running it as a local database component in an on-premise prototype. Eliminating FalkorDB without benchmarking would violate our evidence-based principle.
  * **Memgraph vs Neo4j:** Memgraph's in-memory C++ engine promises high traversal speed, but Neo4j's Graph Data Science (GDS) library and memory management on constrained hardware remain formidable.
  * **Conclusion:** Do **NOT** declare a winner or eliminate FalkorDB. Retain all three under **`BENCHMARK` / `INVESTIGATE`** in our benchmark harness.

---

### E. Graph Visualization: Cytoscape.js vs Sigma.js
* **Radar Hypothesis:** *"Sigma.js should replace Cytoscape.js for performance."*
* **Verification & Evidence:**
  * Sigma.js uses WebGL, making it superior for displaying massive, chaotic graphs (50k+ nodes).
  * However, our core investigator experience relies on a **Target-Centric Concentric Ring Layout (Red $\rightarrow$ Yellow $\rightarrow$ Green)** with clickable edge provenance panels.
  * Cytoscape.js natively supports parameterized concentric layouts and rich DOM/canvas interaction out of the box. Sigma.js would require complex custom coordinate generation in Graphology.
  * Our prototype graphs for an individual suspect cluster are typically under 2,000 active nodes.
  * **Conclusion:** Do **NOT** replace Cytoscape.js. Keep Cytoscape.js as the primary candidate (`[INVESTIGATE]`) and evaluate Sigma.js only if rendering bottlenecks emerge.

---

## 4. Candidate List for Benchmark Specification v2

The following candidates are officially accepted into the candidate roster for empirical benchmarking and prototype validation:

1. **Observation Engines:** Autopsy (`[INVESTIGATE]`) vs IPED (`[INVESTIGATE]`)
2. **Entity Resolution:** Rule-based Normalizer (`[PROPOSAL]`) vs Splink (`[INVESTIGATE]`)
3. **Face Embedding Models:** InsightFace (ArcFace) vs FaceNet vs OpenCV SFace (`[BENCHMARK]`)
4. **Graph Databases:** Memgraph (`[BENCHMARK]`) vs FalkorDB (`[INVESTIGATE]`) vs Neo4j (`[BENCHMARK]`)
5. **Graph Visualizers:** Cytoscape.js (`[INVESTIGATE]`) vs Sigma.js (`[INVESTIGATE]`)
