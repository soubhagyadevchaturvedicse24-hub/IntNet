# Benchmark Specification: InsightFace vs CompreFace (Facial Recognition Layer)

**Document Version:** 1.0.0  
**Status:** `[PROPOSED / OPEN]` (Benchmark Specification)  
**Date:** 2026-09-05  
**Candidate Technologies:** **In-Process Modular InsightFace (`FaceEmbeddingService`)** vs **CompreFace (REST Microservice)**  

---

## 1. Objective
To evaluate whether an in-process, model-agnostic Python library interface (wrapping **InsightFace / ArcFace**) or a standalone **CompreFace** REST microservice is the superior architecture for facial embedding extraction and synthetic FIR suspect matching in CRIMENET.

---

## 2. Hypothesis
* *Hypothesis 1:* The in-process modular Python interface delivers lower latency (avoiding HTTP serialization, network overhead, and database roundtrips) and consumes drastically less RAM than CompreFace's multi-container stack.
* *Hypothesis 2:* Both approaches yield identical facial verification accuracy (ROC-AUC / Precision@Recall) when using the same underlying ArcFace / ResNet backbone weights.

---

## 3. Dataset / Fixture
* **Synthetic Suspect Gallery Dataset (`SYN-FIR-FACES-500`):**
  * 500 reference photographs representing known persons in synthetic FIR records (controlled lighting, frontal orientation).
* **Probe Evidence Photo Dataset (`SYN-PROBE-FACES-100`):**
  * 100 probe images extracted from synthetic forensic evidence images (containing 50 true positive matches with varying pose/illumination and 50 distractor faces).
  * Deterministic Checksum: `sha256:d82e85a083d09a5b3a4a0c8413f1737f09318b82451be8c9c72e2cf573887c2b`.

---

## 4. Environment
* **Host Runtime:** Python 3.12 / ONNX Runtime / PyTorch (CPU mode and optional CUDA GPU mode).
* **CompreFace Deployment:** Docker Compose stack (CompreFace Core + CompreFace UI + PostgreSQL + pgvector).
* **Hardware Allocation:** 4 CPU cores, 8 GB RAM maximum limit.

---

## 5. Procedure
1. **Gallery Enrollment Phase:**
   * Ingest and generate 512-d vector embeddings for all 500 synthetic FIR reference photos.
   * Record enrollment duration (seconds) and memory consumed.
2. **Probe Query Execution ($N=100$ probe photos):**
   * *Track A (In-Process):* Call `FaceEmbeddingService.extract_embedding(image)` $\rightarrow$ perform local cosine similarity against gallery in memory / vector index.
   * *Track B (CompreFace):* Post image to `/api/v1/recognition/recognize` endpoint over local HTTP.
   * Measure single-image inference latency (ms) and end-to-end match latency.
3. **Batch Processing Throughput:**
   * Process a batch of 50 images concurrently; record images processed per second.
4. **Accuracy & Discrimination Validation:**
   * Compute Cosine Similarity scores; calculate True Positive Rate (TPR), False Positive Rate (FPR), and ROC-AUC curve on the 100 probe images.
5. **System Resource Monitoring:**
   * Measure idle RAM, active inference RAM, CPU load %, and disk footprint of both architectures.

---

## 6. Metrics (Mapped to Methodology)
* **Performance:** Single-image match latency (ms P50, P95, P99), batch throughput (images/sec).
* **Resource Usage:** Total system RAM (MB for in-process library vs total Docker RAM for CompreFace stack).
* **Correctness:** Match accuracy (Precision, Recall, ROC-AUC) on ground truth synthetic pairs.
* **Deployment Complexity:** Number of required background containers and services.
* **Integration Effort:** Lines of code required to connect into the FastAPI backend and Evidence Contract.

---

## 7. Repetitions
* 3 complete gallery enrollment passes; 100 randomized probe match queries repeated 5 times.

---

## 8. Expected Output
* Benchmark results log (`BENCHMARKS/reports/face_recognition_benchmark_results.json`).
* Precision-Recall curve and latency breakdown table.

---

## 9. Acceptance Criteria
* **Single Query Latency (CPU):** Match latency $< 250\text{ ms}$ per probe on CPU.
* **Batch Throughput (CPU):** $\ge 5\text{ images/second}$.
* **Accuracy:** ROC-AUC $\ge 0.98$ on controlled synthetic probe set.
* **Memory Budget:** Total facial recognition memory overhead $< 1.5\text{ GB}$ on host.

---

## 10. Threats to Validity
* CPU vs GPU execution discrepancies (testing must be performed with CPU-only mode explicitly specified to guarantee fairness on non-GPU machines).
* ONNX Runtime optimization levels applied in-process vs inside CompreFace container.

---

## 11. What Result Would Change the Architectural Decision
* **Select CompreFace if:** CompreFace provides unique gallery management or security capabilities that outweigh its multi-container footprint and network latency.
* **Retain In-Process Modular Interface if:** In-process embedding achieves equal or better accuracy with $< 50\%$ latency and $< 20\%$ RAM overhead compared to the multi-container stack.
