# CRIMENET Technology Benchmark & Evaluation Methodology

**Document Version:** 1.0.0  
**Status:** `[BASELINE]` (Standard Evaluation Protocol)  
**Date:** 2026-09-05  

---

## 1. Purpose & Principles

This methodology establishes a rigorous, standardized, and reproducible process for benchmarking and evaluating candidate technologies across the CRIMENET Intelligence Lab architecture.

### Fundamental Principles
1. **Evidence-Based Decisions:** No technology is chosen or eliminated based on marketing claims, vendor whitepapers, or popularity.
2. **Identical Workloads:** Competing candidates must be evaluated against the exact same deterministic dataset fixtures under identical host constraints.
3. **Decoupled Architecture Preservation:** Benchmarks must test technologies behind clean interface boundaries so that swapping a candidate requires zero changes to adjacent layers.
4. **Reproducibility First:** Every benchmark execution must log full hardware, OS, version, configuration, dataset hash, and execution parameters.

---

## 2. Standard Evaluation Criteria (12 Dimensions)

Every candidate technology in CRIMENET is evaluated across twelve standardized dimensions:

| # | Dimension | Definition & Scope | Key Metrics / Evidence Required |
|---|---|---|---|
| 1 | **Capability** | Functional coverage of required domain features. | Direct feature checklist against Evidence Contract and pipeline requirements. |
| 2 | **Correctness** | Accuracy, mathematical validity, and output consistency. | Zero false drops, correct path traversal results, precision/recall on ground truth. |
| 3 | **Performance** | Throughput, latency distribution, and scalability. | P50, P95, P99 latency (ms), records/sec throughput, queries/sec under load. |
| 4 | **Resource Usage** | Hardware footprint under idle and peak execution. | Peak RAM (RSS MB), CPU core utilization %, disk I/O throughput, GPU VRAM (if applicable). |
| 5 | **Reliability** | Stability under sustained stress and fault handling. | Error rate under concurrency, crash recovery time, data consistency after abrupt stop. |
| 6 | **Deployment Complexity** | Simplicity of installation, runtime dependencies, and configuration. | Container footprint, number of auxiliary services, configuration file complexity. |
| 7 | **Integration Effort** | Cleanliness of Python/TypeScript APIs and schema mapping. | Lines of adapter code required, asynchronous driver support, type safety. |
| 8 | **Offline / Air-Gapped** | Full functionality without internet connectivity. | Zero outbound telemetry, no remote license server dependencies, offline package install. |
| 9 | **Licensing** | Legal compliance with open-source and distribution requirements. | License verification (MIT, Apache 2.0, BSL 1.1, GPL v3, SSPL), absence of cloud-only restrictions. |
| 10 | **Maintainability** | Documentation quality, active community, and ecosystem longevity. | Release cadence, issue resolution activity, clarity of official reference documentation. |
| 11 | **Explainability / Provenance** | Ability to trace and explain every derived link and score. | Native retention of source file IDs, byte offsets, confidence scores, and execution logs. |
| 12 | **Prototype Suitability** | Appropriateness for rapid local single-node demonstration. | Minimal developer friction, instant reset capability, low cognitive overhead for demo. |

---

## 3. Benchmark Reproducibility Record Requirements

To ensure any team member or reviewer can replicate benchmark results independently, every benchmark execution report must record the following mandatory environmental metadata:

```yaml
benchmark_execution_metadata:
  timestamp_utc: "YYYY-MM-DDTHH:MM:SSZ"
  environment:
    os_name: "Windows 11 Pro / Ubuntu 22.04 LTS"
    os_version_build: "10.0.22631"
    cpu_model: "Intel Core i7-XXXX / AMD Ryzen X"
    cpu_cores_physical: 8
    cpu_threads_logical: 16
    cpu_base_frequency_ghz: 3.2
    ram_total_physical_gb: 32.0
    ram_allocated_limit_gb: 16.0
    gpu_model: "NVIDIA RTX XXXX / None (CPU-Only)"
    gpu_vram_gb: 8.0
    gpu_driver_cuda_version: "550.54 / CUDA 12.4"
  software_under_test:
    candidate_name: "Candidate Name"
    exact_version: "vX.Y.Z"
    runtime_environment: "Docker 24.0.7 / Python 3.12.2 / Java 17"
    container_image_digest: "sha256:..."
    configuration_flags:
      - "--flag1=value"
      - "--flag2=value"
  workload_fixture:
    dataset_name: "synthetic_crime_network_21.5k"
    dataset_version: "1.0.0"
    dataset_sha256_checksum: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    generator_script_version: "scripts/generate_synthetic_graph.py (git commit: abc1234)"
    random_seed: 20260905
  execution_protocol:
    warmup_runs: 5
    measured_repetitions: 100
    concurrency_threads: 1
    statistical_metrics:
      - "min"
      - "mean"
      - "median_p50"
      - "p95"
      - "p99"
      - "max"
      - "std_dev"
```

---

## 4. Benchmark Specification Structure Standard

All individual candidate benchmark specifications must adhere strictly to this 11-point template:

1. **Objective:** What specific architectural question does this benchmark answer?
2. **Hypothesis:** The explicit, testable assumption being evaluated.
3. **Dataset / Fixture:** Deterministic data sources, node/edge counts, file formats, and checksums.
4. **Environment:** Hardware baseline, execution boundaries, and container limits.
5. **Procedure:** Step-by-step execution protocol (Setup $\rightarrow$ Warmup $\rightarrow$ Measurement $\rightarrow$ Teardown).
6. **Metrics:** Measured variables mapped to the 12 evaluation criteria.
7. **Repetitions:** Statistical sampling design ($N$ runs, warmup count, confidence intervals).
8. **Expected Output:** Concrete schema of the resulting benchmark data artifact.
9. **Acceptance Criteria:** Precise numerical thresholds required for a candidate to pass.
10. **Threats to Validity:** Confounding variables, caching effects, or synthetic data biases.
11. **What Result Would Change the Architectural Decision:** The exact empirical findings that would cause a candidate to be selected, replaced, or rejected.

---

## 5. Decision Lifecycle

```text
[BENCHMARK SPECIFICATION (PROPOSAL)]
                ↓
[TEST HARNESS & SYNTHETIC DATASET SETUP]
                ↓
[EMPIRICAL EXECUTION & MEASUREMENT]
                ↓
[BENCHMARK REPORT WITH REPRODUCIBILITY LOG]
                ↓
[ARCHITECTURAL DECISION RECORD (ADR) DRAFT]
                ↓
[HUMAN REVIEW & FINAL ACCEPTANCE]
```
