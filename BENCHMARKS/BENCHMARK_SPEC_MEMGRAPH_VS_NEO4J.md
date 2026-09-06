# Benchmark Specification: Memgraph vs Neo4j (Graph Database Engine)

**Document Version:** 2.0.0  
**Status:** `[PROPOSED / OPEN]` (Benchmark Specification)  
**Date:** 2026-09-05  
**Primary Comparison:** **Memgraph** vs **Neo4j**  
**Secondary Track:** **FalkorDB** retained under `[INVESTIGATE]` for matrix-traversal benchmarking.  

---

## 1. Objective
To empirically evaluate the traversal performance, memory footprint, algorithm latency (PageRank / Centrality), and local operational simplicity of **Memgraph** versus **Neo4j** (and **FalkorDB** as an investigative candidate) under an identical synthetic crime-network workload.

---

## 2. Hypothesis
* *Hypothesis 1:* Memgraph's in-memory C++ architecture yields significantly lower P95/P99 latency on 2-hop, 3-hop, and shortest-path Cypher traversals compared to Neo4j.
* *Hypothesis 2:* Neo4j exhibits a higher cold-start memory overhead due to the JVM, but its Graph Data Science (GDS) library provides mature community detection and projection algorithms.
* *Hypothesis 3:* FalkorDB's GraphBLAS matrix engine offers competitive traversal speeds with minimal RAM footprint.

---

## 3. Dataset / Workload Fixture `[BASELINE]`
* **Total Volume:** **21,500 Nodes** and **40,000 Edges** generated deterministically (`seed=20260905`).
* **Node Breakdown (21,500 nodes):**
  * `Person`: 1,000 (`id`, `name`, `fir_ref`, `risk_score`)
  * `PhoneNumber`: 5,000 (`number`, `carrier`, `imei_ref`)
  * `Vehicle`: 2,000 (`license_plate`, `make`, `model`, `color`)
  * `Location`: 3,000 (`location_id`, `latitude`, `longitude`, `zone`)
  * `Organization`: 500 (`org_id`, `name`, `org_type`)
  * `Event`: 10,000 (`event_id`, `event_type`, `timestamp`)
* **Edge Breakdown (40,000 edges):**
  * `CALLED`: 15,000 (`timestamp`, `duration_sec`, `evidence_id`)
  * `USED_PHONE`: 3,000 (`since_date`, `is_primary`, `evidence_id`)
  * `USED_VEHICLE`: 2,500 (`association_type`, `evidence_id`)
  * `VISITED`: 6,000 (`timestamp`, `dwell_time_min`, `evidence_id`)
  * `ASSOCIATED_WITH`: 1,000 (`role`, `confidence`, `evidence_id`)
  * `CONNECTED_TO`: 4,500 (`weight`, `confidence`, `evidence_id`)
  * `PARTICIPATED_IN`: 8,000 (`role`, `evidence_id`)

---

## 4. Environment
* **Host Machine:** Windows 11 x64 / Docker Desktop 24.0+.
* **Resource Limits per Container:** Pinned to 4 CPU cores, 8 GB RAM maximum limit.
* **Memgraph Container:** `memgraph/memgraph-platform:latest` (or standalone `memgraph/memgraph:latest`).
* **Neo4j Container:** `neo4j:5-community` (with GDS plugin enabled).
* **FalkorDB Container:** `falkordb/falkordb:latest`.

---

## 5. Procedure
1. **Container Initialization:** Start fresh isolated Docker container; measure time to accept Bolt/Cypher connections (cold startup).
2. **Bulk Ingestion:** Load 21.5k nodes and 40k edges via parameterized batch `UNWIND` Cypher transactions; build indexes on `Person.id`, `PhoneNumber.number`, `Location.location_id`.
3. **Warmup Phase:** Run 10 sample 1-hop traversals.
4. **Query Suite Execution ($N=100$ randomized repetitions per test):**
   * *Test Q1 (1-Hop):* Immediate neighbor expansion.
   * *Test Q2 (2-Hop):* Co-occurrence and mutual contact discovery.
   * *Test Q3 (3-Hop):* Multi-layered syndicate chain traversal.
   * *Test Q4 (Shortest Path):* $k$-hop path between 50 suspect pairs.
   * *Test Q5 (Centrality):* PageRank / Betweenness centrality calculation.
   * *Test Q6 (Community Detection):* Louvain / WCC cluster identification.
   * *Test Q7 (Provenance Lookup):* Edge evidence attribute retrieval for UI.
   * *Test Q8 (Concurrency / Update):* 10 read threads while inserting 500 edges/sec.
5. **Memory & Footprint Capture:** Measure idle RAM, peak RAM during PageRank, container image disk size.
6. **Teardown & Reset:** Measure time to wipe database and return to clean state.

---

## 6. Metrics (Mapped to Methodology)
* **Performance:** P50, P95, P99 latency (ms) across all query categories; bulk insert records/sec.
* **Resource Usage:** Idle RAM (MB), peak execution RAM (MB), CPU core % load.
* **Reliability:** Error rate under concurrent read/write load.
* **Integration & Ergonomics:** Python client latency (`neo4j` driver vs `pymgclient` vs `falkordb-py`).
* **Licensing:** Verification of BSL 1.1 vs GPL v3 vs SSPL for local distribution.

---

## 7. Repetitions
* 5 warmup iterations followed by 100 timed iterations per query type with randomized target IDs.

---

## 8. Expected Output
* Benchmark results artifact (`BENCHMARKS/reports/graph_db_benchmark_results.json`).
* Summary comparison table across latency percentiles and memory consumption.

---

## 9. Acceptance Criteria
* **1-Hop & 2-Hop Latency:** P95 latency $< 15\text{ ms}$.
* **3-Hop Latency:** P95 latency $< 100\text{ ms}$.
* **Centrality Calculation:** Complete PageRank on 21.5k nodes in $< 2.0\text{ seconds}$.
* **Memory Ceiling:** Peak memory must stay below 4 GB on the host machine.

---

## 10. Threats to Validity
* JVM garbage collection pauses in Neo4j during long test runs.
* In-memory caching differences between cold and warm queries.
* Bolt protocol client driver serialization overhead vs server execution time.

---

## 11. What Result Would Change the Architectural Decision
* **Select Memgraph if:** Traversal and algorithm latency is consistently $>3\times$ faster than Neo4j with lower RAM footprint, and BSL license terms are acceptable for prototype distribution.
* **Select Neo4j if:** GDS algorithm ecosystem and stability outperform Memgraph on complex graph analytics, and JVM resource usage remains acceptable.
* **Select FalkorDB if:** Matrix-based GraphBLAS operations yield superior latency and ultra-low RAM usage while license terms are confirmed compatible.
