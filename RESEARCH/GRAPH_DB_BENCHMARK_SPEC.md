# Graph Database Benchmark Specification: Memgraph vs FalkorDB vs Neo4j

**Document Version:** 1.0.0  
**Status:** `[PROPOSAL]` (Benchmark methodology & protocol definition)  
**Date:** 2026-09-05  
**Candidate Databases:** **Memgraph** | **FalkorDB** | **Neo4j**  
**Guiding Principle:** Decision must be backed by empirical measurements on an identical synthetic crime-network workload; no vendor claims accepted as benchmarks.

---

## 1. Objective & Benchmark Principles

The objective of this specification is to define a fair, reproducible, and automated benchmarking harness to compare **Memgraph**, **FalkorDB**, and **Neo4j** under a representative **Crime Linkage Detector** workload.

### Guiding Rules
1. **Identical Hardware & Environment:** All tests must run on the same physical host machine under controlled conditions (pinned CPU cores, specified RAM limits, isolated Docker daemon).
2. **Identical Workload & Dataset:** All engines must be loaded with the exact same synthetic dataset generated from a deterministic random seed.
3. **OpenCypher Compatibility:** Queries must be written in standard OpenCypher / Cypher to ensure functional equivalence.
4. **Clean Abstraction:** Processing and API layers will interact via an abstraction interface (`GraphRepository`), preventing vendor lock-in during and after the benchmark.

---

## 2. Candidate Profiles & Architectural Assumptions

| Candidate | Core Architecture | Primary Query Language | Python Driver | Default Deployment | License Profile | Status |
|---|---|---|---|---|---|---|
| **Memgraph** | In-memory C++ graph engine with on-disk snapshotting. | OpenCypher | `pymgclient` / `neo4j` bolt / `gqlalchemy` | Docker (`memgraph/memgraph-platform`) | BSL 1.1 / Apache 2.0 modules | `[EXPERIMENTAL]` |
| **FalkorDB** | Low-latency graph engine (Redis-derived / C with GraphBLAS matrix math). | OpenCypher | `falkordb-py` | Docker (`falkordb/falkordb`) | Server Side Public License (SSPL) / Custom | `[EXPERIMENTAL]` |
| **Neo4j** | Established Java-based native property graph engine. | Cypher | `neo4j` (Official Bolt driver) | Docker (`neo4j:5-community`) | GPL v3 (Community) / Commercial | `[EXPERIMENTAL]` |

---

## 3. Synthetic Crime-Network Benchmark Dataset Specification

To test real-world investigative link discovery, the dataset represents a multi-modal criminal network with intentional dense clusters, multi-hop chains, and cross-entity associations.

### Entity Schema (Nodes) — Target Volume: 21,000 Nodes `[BASELINE]`

| Label | Target Count | Key Properties |
|---|---|---|
| `Person` | 1,000 | `id`, `name`, `fir_reference`, `national_id_hash`, `risk_score` |
| `PhoneNumber` | 5,000 | `number`, `carrier`, `registered_name`, `imei_ref` |
| `Vehicle` | 2,000 | `license_plate`, `make`, `model`, `color`, `vin_hash` |
| `Location` | 3,000 | `location_id`, `latitude`, `longitude`, `zone`, `address` |
| `Organization` | 500 | `org_id`, `name`, `org_type` (`"Business"`, `"ShellCompany"`, `"Club"`) |
| `Event` | 10,000 | `event_id`, `event_type` (`"Incident"`, `"Meeting"`, `"Transaction"`), `timestamp` |

---

### Relationship Schema (Edges) — Target Volume: 40,000 Relationships `[BASELINE]`

| Relationship Type | Source $\rightarrow$ Target | Key Properties | Target Volume |
|---|---|---|---|
| `CALLED` | `PhoneNumber` $\rightarrow$ `PhoneNumber` | `timestamp`, `duration_sec`, `call_type`, `evidence_id` | 15,000 |
| `USED_PHONE` | `Person` $\rightarrow$ `PhoneNumber` | `since_date`, `is_primary`, `evidence_id` | 3,000 |
| `USED_VEHICLE` | `Person` $\rightarrow$ `Vehicle` | `association_type` (`"Owner"`, `"Driver"`), `evidence_id` | 2,500 |
| `VISITED` | `Person` $\rightarrow$ `Location` | `timestamp`, `dwell_time_min`, `evidence_id` | 6,000 |
| `ASSOCIATED_WITH` | `Person` $\rightarrow$ `Organization` | `role`, `confidence`, `evidence_id` | 1,000 |
| `CONNECTED_TO` | `Person` $\rightarrow$ `Person` | `weight`, `confidence`, `relationship_type`, `evidence_id` | 4,500 |
| `PARTICIPATED_IN` | `Person` $\rightarrow$ `Event` | `role`, `evidence_id` | 8,000 |

*Deterministic Generation:* Synthetic generator will use `seed=20260905` to generate identical CSV export files for all test runs.

---

## 4. Benchmark Query Suite (Standard Cypher)

All candidate queries must be run with parameterized inputs ($N=100$ random samples per query type) to measure latency distribution (P50, P95, P99).

### 1. Ingestion / Bulk Import Latency
* **Test:** Load the complete synthetic dataset (21k nodes, 40k edges).
* **Cypher Pattern:** Batch `UNWIND` with `CREATE` / `MERGE` and index creation on primary keys (`Person.id`, `PhoneNumber.number`, etc.).
* **Metric:** Total import duration (seconds) and insert throughput (records/sec).

---

### 2. 1-Hop Traversal (Immediate Entity Neighborhood)
* **Investigator Scenario:** Investigator clicks on a Person or Phone to view immediate connections.
* **Cypher:**
  ```cypher
  MATCH (p:Person {id: $person_id})-[r]-(target)
  RETURN type(r) AS rel_type, properties(r) AS rel_props, labels(target) AS target_labels, properties(target) AS target_props
  ```
* **Metric:** Query latency (ms) across 100 sample IDs.

---

### 3. 2-Hop Traversal (Secondary Network & Shared Associations)
* **Investigator Scenario:** Expand network to identify mutual phone numbers, shared vehicles, or co-located individuals.
* **Cypher:**
  ```cypher
  MATCH (p:Person {id: $person_id})-[r1*1..2]-(n)
  RETURN DISTINCT n.id, labels(n), length(r1)
  ```
* **Metric:** Query latency (ms) across 100 sample IDs.

---

### 4. 3-Hop Traversal (Deep Association Chain)
* **Investigator Scenario:** Trace indirect syndicates and multi-layered intermediary links.
* **Cypher:**
  ```cypher
  MATCH (p:Person {id: $person_id})-[r1*1..3]-(n:Person)
  WHERE n.id <> $person_id
  RETURN DISTINCT n.id, count(r1) AS path_count
  ```
* **Metric:** Query latency (ms) and memory pressure.

---

### 5. Shortest Path (Linkage Discovery)
* **Investigator Scenario:** Investigator asks *"How is Suspect A connected to Suspect B?"*
* **Cypher:**
  ```cypher
  MATCH p = shortestPath((p1:Person {id: $p1_id})-[*..6]-(p2:Person {id: $p2_id}))
  RETURN [n in nodes(p) | n.id] AS node_ids, [r in relationships(p) | type(r)] AS rel_types
  ```
* **Metric:** Path computation latency (ms) across 50 connected pairs.

---

### 6. Centrality Scoring (Critical Network Hubs)
* **Investigator Scenario:** Rank entities by influence or connectivity to compute CCC / Concentric Ring positions.
* **Algorithms Tested:**
  * **PageRank**
  * **Degree Centrality**
  * **Betweenness Centrality**
* **Method:** Run native graph algorithms (Memgraph MAGE vs FalkorDB built-ins vs Neo4j Graph Data Science).
* **Metric:** Execution time (ms) and peak memory allocation.

---

### 7. Community Detection (Crime Syndicate Clustering)
* **Investigator Scenario:** Automatically identify discrete sub-networks and criminal rings.
* **Algorithms Tested:** **Louvain** or **Weakly Connected Components (WCC)**.
* **Metric:** Execution time (ms) and cluster partition stability.

---

### 8. Relationship Lookup with Provenance
* **Investigator Scenario:** Investigator clicks an edge; UI requests full supporting evidence metadata.
* **Cypher:**
  ```cypher
  MATCH (p1:Person {id: $p1_id})-[r:CONNECTED_TO]->(p2:Person {id: $p2_id})
  RETURN r.evidence_id, r.confidence, r.weight, r.relationship_type
  ```
* **Metric:** Lookup latency (ms).

---

### 9. Concurrent Read & Real-time Update Latency
* **Investigator Scenario:** System inserts new forensic evidence edges while investigators are querying dashboards.
* **Method:** 10 continuous read threads executing 2-hop traversals while 1 write thread performs 500 edge inserts/second.
* **Metric:** Read latency degradation (%) and write transaction latency (ms).

---

## 5. System & Operational Measurements

| Measurement Category | Metric | Collection Method |
|---|---|---|
| **Memory Utilization** | Idle RAM usage (MB) | Docker stats / OS process monitor before query load. |
| **Memory Utilization** | Peak RAM under 3-hop & Centrality load (MB) | Peak resident set size (RSS) during algorithm execution. |
| **CPU Utilization** | Peak CPU % and core distribution | Docker stats / OS thread accounting. |
| **Startup / Readiness** | Time to accept Cypher query after cold start (sec) | Healthcheck probe loop upon container start. |
| **Python Client Latency** | Network roundtrip + deserialization overhead (ms) | `time.perf_counter()` in Python client driver. |
| **Deployment Footprint** | Container image size & disk storage (MB) | `docker image ls` and volume size on disk. |
| **Reset Simplicity** | Time to wipe database and return to clean state (sec) | `MATCH (n) DETACH DELETE n` or drop database command latency. |

---

## 6. Evaluation Scorecard & Decision Framework

The final database selection will be scored across 5 weighted dimensions:

| Dimension | Weight | Key Evaluation Criteria |
|---|---|---|
| **Query & Traversal Performance** | 30% | P95 latency across 1-hop, 2-hop, 3-hop, and Shortest Path queries. |
| **Graph Analytics & Centrality** | 20% | Native execution speed and simplicity of PageRank, Betweenness, and Community Detection. |
| **Operational & Memory Footprint** | 20% | Local machine RAM consumption, startup speed, and low overhead in local prototype setup. |
| **Python Ecosystem & API Ergonomics** | 15% | Cleanliness of Python driver, type conversion, async support, and connection pooling. |
| **Deployment Simplicity & Licensing** | 15% | Ease of local setup, Docker footprint, and licensing constraints for local/offline deployment. |

---

## 7. Additional Relevant Metrics Identified `[PROPOSAL]`

During the specification design, the following 4 critical metrics were identified as essential for inclusion in the final benchmark execution:

1. **Frontend Serialization Latency (Cytoscape JSON Conversion):**  
   Time taken by the Python API to transform raw graph query results into Cytoscape.js-compatible node/edge JSON structures.
2. **Vector Similarity Query Ergonomics (Hybrid Search):**  
   Evaluation of whether candidate databases support storing face/entity vector embeddings directly alongside graph nodes, or whether an external vector store (e.g., Chroma/FAISS) is required.
3. **Crash Recovery & Persistence Durability:**  
   Time taken to restore graph state after an ungraceful container restart.
4. **License & Air-Gapped Distribution:**  
   Verification that the engine can run completely air-gapped without remote telemetry or license server check-ins.

---

## 8. Status & Next Steps

* **Specification Status:** `[PROPOSAL]` — Ready for review.
* **Prerequisite for Execution:** Generation of synthetic benchmark dataset CSV files (`DATA/benchmarks/crime_network_20k.zip`).
* **Next Action:** Build the automated synthetic generator script and Docker benchmark harness before running measurements.
