# CRIMENET Intelligence Lab — System Architecture

**Document Version:** 1.0.0  
**Status:** `[PROPOSAL]` (Baseline Architecture)  
**Last Updated:** 2026-09-05  

---

## 1. System Mission & Core Boundaries

The **Crime Linkage Detector** is an AI-assisted decision-support system designed to help human investigators connect evidence across disparate forensic and operational sources, construct explainable criminal-network graphs, detect critical contacts and associations, and present defensible analytical reasoning.

### Non-Negotiable Boundaries `[BASELINE]`
* **Investigator Decision Support Only:** The system assists human investigators; it does **not** determine guilt or label individuals as "guilty" or "criminal".
* **Analytical Terminology:** *Lead, Indicator, Potential Association, Confidence, Analytical Insight, Supporting Evidence, Human Verification*.
* **Forensic Decoupling:** The observation engine (e.g., Autopsy, IPED) is strictly an *examination tool*, not the product. All downstream analytics consume a stable, versioned **Normalized Evidence Contract**.
* **Evidence Provenance:** Every graph node, edge, match score, and timeline entry retains an unbroken provenance chain back to the physical source file, byte offset, hash, and timestamp.
* **Asynchronous Execution:** Long-running forensic ingestion and batch processing operate asynchronously with observable job lifecycle states.

---

## 2. End-to-End Conceptual Pipeline

```text
+-------------------------------------------------------------------------+
|                         FORENSIC DATA SOURCES                           |
|       (Synthetic Disk Images: E01, RAW, Logical Dumps, Loose Files)     |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                  FORENSIC OBSERVATION LAYER [CANDIDATE]                 |
|                   (Candidates: Autopsy, IPED)                           |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|               NORMALIZED EVIDENCE CONTRACT [v1.0.0 PROPOSAL]            |
|       (Decoupled JSON Schema: Provenance, Artifacts, Metadata)          |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                         PROCESSING LAYER [MODULAR]                      |
|   - Face Recognition Service (Model-Agnostic Interface) [BENCHMARK]     |
|   - Entity Resolution & Record Linkage (Rule Engine / Splink) [PROPOSAL]|
|   - Critical Contact & Network Scoring (CCC Algorithm) [PROPOSAL]      |
|   - Graph Construction & Normalization [PROPOSAL]                       |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                  GRAPH DATABASE ENGINE [CANDIDATES]                     |
|              (Candidates: Memgraph, FalkorDB, Neo4j)                    |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                         BACKEND API LAYER [FASTAPI]                     |
|   - Asynchronous Job Queue & Status Monitor                             |
|   - Cypher Query Service & Graph Serialization                          |
|   - "Why Linked?" Provenance Resolution Service                         |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                  INVESTIGATOR DASHBOARD [REACT + TS]                    |
|   - Concentric Ring Visualizer (Cytoscape.js / Sigma.js)                |
|   - Interactive Evidence & Provenance Inspector ("Why Linked?")         |
|   - Human Verification & Case Triage Action Panel                       |
+-------------------------------------------------------------------------+
```

---

## 3. Component Layer Breakdown

### Layer 1: Forensic Observation & Extraction
* **Role:** Ingest forensic images, parse file systems, extract media/metadata, and recover known/deleted artifacts.
* **Candidates Under Evaluation:** **Autopsy** (`[INVESTIGATE]`) vs **IPED** (`[INVESTIGATE]`).
* **Output:** Case SQLite database, CASE-UCO JSON reports, and carved media files.

### Layer 2: Normalized Evidence Contract
* **Role:** Architectural insulation boundary preventing downstream tools from depending on observation engine internals.
* **Specification:** `RESEARCH/EVIDENCE_CONTRACT_V1.md`.
* **Standard Fields:** Envelope, Source Provenance, File Metadata, Hashes, Timestamps, Extracted Media, Entities, Relationships, Timeline Events, Engine Traceability.

### Layer 3: Modular Processing Pipelines
* **Facial Recognition:** Model-agnostic Python interface (`FaceEmbeddingService`) comparing extracted faces against synthetic FIR databases.
* **Entity Resolution:** Probabilistic deduplication of noisy names, phone numbers, and addresses (evaluating **Splink** vs deterministic rules).
* **Critical Contact / CCC Scoring:** Mathematical formulation weighting communication frequency, timeline proximity, and association confidence to place nodes into Red/Yellow/Green rings.

### Layer 4: Graph Storage & Analytics
* **Role:** Property graph storage, Cypher query execution, multi-hop traversals, shortest path resolution, and community/centrality algorithms.
* **Candidates Under Evaluation:** **Memgraph** (`[BENCHMARK]`) vs **FalkorDB** (`[INVESTIGATE]`) vs **Neo4j** (`[BENCHMARK]`).

### Layer 5: Backend API & Service Layer
* **Role:** Coordinate async ingest jobs, expose REST/WebSocket endpoints, run Cypher queries, and package Cytoscape-compatible graph payloads.
* **Framework:** **FastAPI** (`[KEEP]`).

### Layer 6: Investigator Dashboard
* **Role:** Interactive investigative workspace.
* **Components:**
  * Concentric layout rendering suspects in Red (high confidence/critical), Yellow (moderate), Green (peripheral) rings.
  * Node/Edge Inspector answering *"Why Are They Linked?"* with source image paths, byte offsets, and SHA-256 hashes.
  * Investigator Verification controls to accept, flag, or refute analytical leads.
* **Visualization Candidates:** **Cytoscape.js** (`[INVESTIGATE]`) vs **Sigma.js** (`[INVESTIGATE]`).

---

## 4. Architectural Decision Log Index

All major architectural choices are tracked via Architectural Decision Records in `DECISIONS/`:
* `ADR-001`: Product Platform & Local Deployment (`[PROPOSED / OPEN]`)
* `ADR-002`: Forensic Observation Engine Selection (`[PROPOSED / OPEN]`)
* `ADR-003`: Normalized Evidence Contract Decoupling (`[PROPOSED / OPEN]`)
* `ADR-004`: Graph Database Engine Selection (`[PROPOSED / OPEN]`)
* `ADR-005`: Investigator Graph Visualization Library (`[PROPOSED / OPEN]`)
* `ADR-006`: Facial Recognition Architecture & Interface (`[PROPOSED / OPEN]`)
* `ADR-007`: Entity Resolution & Record Linkage Engine (`[PROPOSED / OPEN]`)
