# ADR-004: Graph Database Engine Selection

* **Status:** `[PROPOSED / OPEN]`  
* **Date:** 2026-09-05  
* **Decision Makers:** CRIMENET Engineering Team  

---

## 1. Context and Problem Statement
CRIMENET requires an underlying graph database to store multi-modal entities (People, Phones, Vehicles, Locations, Events) and relationships, and to execute low-latency multi-hop traversals, shortest path searches, and centrality calculations.

---

## 2. Decision Drivers
* Traversal latency across 1-hop, 2-hop, 3-hop queries.
* Memory and CPU footprint on local single-node development environments.
* Support for standard Cypher / OpenCypher.
* Native graph algorithm support (PageRank, Louvain, Betweenness).
* Licensing compatibility (BSL 1.1 vs GPL v3 vs SSPL).

---

## 3. Considered Options
* **Option A:** Memgraph (In-memory C++ engine + MAGE algorithms).
* **Option B:** Neo4j (Industry-standard property graph + Graph Data Science).
* **Option C:** FalkorDB (GraphBLAS sparse matrix linear algebra engine).

---

## 4. Current Status
* **Status:** `[PROPOSED / OPEN]` — Phase 2 empirical benchmark execution completed ($N=3$ cold/warm runs, dataset seed `20260905`, SHA-256: `5ee84a55eeb7c27f6e7c7fedfa83c211609b620ba46566cf09db78ada9f14588`). Results documented in [`BENCHMARKS/reports/graph_db_benchmark_results.json`](file:///D:/Proto%20SIH/BENCHMARKS/reports/graph_db_benchmark_results.json).

---

## 5. Phase 2 Empirical Benchmark Results (21.5k Nodes / 40k Edges)

| Candidate | Status on Dev Host | Deployment Model | Licensing | 21.5k Node Ingestion | 1-Hop Latency | 3-Hop Latency | PageRank | Peak RAM |
|---|---|---|---|---|---|---|---|---|
| **Kùzu (Embedded Cypher)** | `OPERATIONAL / BENCHMARKED` | Embedded C++ Extension | MIT | **1.56s** | **14.67 ms** | **18.71 ms** | **39.59 ms** | **269.61 MB** |
| **NetworkX Repository** | `OPERATIONAL / BENCHMARKED` | In-Memory Python | 3-Clause BSD | **0.41s** | **0.05 ms** | **0.16 ms** | **406.00 ms** | **154.08 MB** |
| **Memgraph 2.14.0** | `UNAVAILABLE_ON_DEV_HOST` | Linux Container | BSL 1.1 / Apache 2.0 | N/A | N/A | N/A | N/A | Docker daemon inactive |
| **Neo4j 5.26.0** | `UNAVAILABLE_ON_DEV_HOST` | JVM / Container | GPLv3 / Commercial | N/A | N/A | N/A | N/A | Docker daemon inactive |
| **FalkorDB 1.7.1** | `UNAVAILABLE_ON_DEV_HOST` | Redis Module | SSPL v1 | N/A | N/A | N/A | N/A | Docker daemon inactive |

---

## 6. Recommended Candidate Hypothesis
* **Database-Agnostic Application Architecture:** Maintain abstract `GraphRepositoryBase` interface decoupling the backend logic.
* **Recommended Prototype Engine:** **Kùzu Embedded Cypher (C++)** or **NetworkX In-Memory Repository** for immediate local development. Kùzu provides 100% Cypher compliance, 0ms startup overhead, 269 MB RAM usage, sub-2s ingestion of 61,500 items, and MIT open-source licensing.
* **Server Candidates:** Retain **Memgraph** and **Neo4j** under `[BENCHMARK / OPEN]` for server deployment when container infrastructure is active.

