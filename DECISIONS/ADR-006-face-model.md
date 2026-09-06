# ADR-006: Facial Recognition Architecture & Interface

* **Status:** `[PROPOSED / OPEN]`  
* **Date:** 2026-09-05  
* **Decision Makers:** CRIMENET Engineering Team  

---

## 1. Context and Problem Statement
CRIMENET requires a face recognition pipeline to extract embeddings from photographic evidence and match them against a synthetic FIR gallery without locking into fixed vector dimensions or creating excessive container overhead.

---

## 2. Decision Drivers
* Model-agnostic embedding interface (swappable weights and vector lengths).
* Low latency on CPU/GPU host environments.
* Minimal multi-container architectural footprint.
* Precision / recall on controlled suspect photo galleries.

---

## 3. Considered Options
* **Option A:** In-Process Python Modular Interface (`FaceEmbeddingService` wrapping InsightFace/ArcFace).
* **Option B:** Standalone Microservice (CompreFace REST API with PostgreSQL/pgvector).
* **Option C:** External Cloud Cognitive API (AWS Rekognition / Azure Face — Incompatible with offline baseline).

---

## 4. Current Status
* `[PROPOSED / OPEN]` — Pending execution of `BENCHMARKS/BENCHMARK_SPEC_INSIGHTFACE_VS_COMPREFACE.md`.

---

## 5. Evidence & Verification Required to Finalize
* Empirical benchmark measuring single/batch inference latency, RAM overhead, and verification accuracy on synthetic FIR photos.
