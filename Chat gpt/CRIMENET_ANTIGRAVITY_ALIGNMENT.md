# CRIMENET Intelligence Lab — Agent Alignment Context

## Purpose

This file is the implementation-facing context for AI coding agents working on the Crime Linkage Detector project.

Use this document together with the project baseline documents and the repository code. Do not treat this file as permission to invent facts, tools, datasets, capabilities, versions, or architecture decisions.

The project principle is:

> Build less. Discover more. Validate everything. Build only what matters.

---

## 1. Project Mission

The Crime Linkage Detector is intended to assist investigators by connecting evidence from multiple sources, extracting entities and relationships, constructing an explainable criminal-network-style graph, identifying potentially important associations, and presenting the analytical reasoning to a human investigator.

The system assists investigators. It does not determine guilt.

Preferred analytical language:

- Lead
- Indicator
- Potential Association
- Confidence
- Analytical Insight
- Supporting Evidence
- Human Verification

Avoid automatically describing a person as guilty or criminal.

---

## 2. Baseline Architecture

Preserve the existing conceptual pipeline unless new evidence justifies a change:

```text
Data Sources
    ↓
Data Collection
    ↓
Acquisition / Imaging
    ↓
Preprocessing
    ↓
Structured + Unstructured Processing
    ↓
NLP / Entity Extraction
    ↓
Relationship Extraction
    ↓
Entity Resolution
    ↓
Graph Construction
    ↓
Pattern / Anomaly Detection
    ↓
Network Analysis
    ↓
Confidence Prediction
    ↓
Severity + CCC
    ↓
Investigator Dashboard
    ↓
Actionable Intelligence
```

Core entities:

- People
- Phone Numbers
- Vehicles
- Locations
- Organizations
- Events

Example relationships:

- Person → Called → Phone Number
- Person → Used → Vehicle
- Person → Visited → Location
- Person → Associated With → Organization
- Person → Connected To → Person

---

## 3. Current Product Direction

The preferred first implementation is a local web application.

### Frontend

- React
- TypeScript
- Cytoscape.js for investigator graph visualization

### Backend

- Python
- FastAPI

### Observation Engine

- Autopsy

### Processing

Modular Python workflows.

### Graph Database Candidates

Benchmark before selecting:

- Memgraph
- FalkorDB
- Neo4j

Do not declare a winner based only on marketing claims.

### Deployment

A local deployment is preferred for the prototype.

Docker or Docker Compose may be used where it improves reproducibility, but do not force Autopsy into a container without validating that approach on the target environment.

---

## 4. Critical Architectural Boundary

The application should hide the internal forensic engine from the investigator.

Preferred conceptual flow:

```text
FORENSIC IMAGE
      ↓
OUR APPLICATION
      ↓
OBSERVATION ENGINE
   (AUTOPSY)
      ↓
EVIDENCE NORMALIZATION CONTRACT
      ↓
PROCESSING
      ↓
GRAPH + ANALYTICS
      ↓
CONCLUSION
      ↓
INVESTIGATOR DASHBOARD
```

Autopsy is an observation/examination engine, not the product.

The frontend should not depend directly on undocumented Autopsy database internals.

The Processing layer should consume a stable normalized Evidence Contract so that Autopsy can eventually be replaced without redesigning the Processing and Conclusion layers.

---

## 5. Forensic Evidence Model

Maintain the distinction:

```text
Original Evidence
      ↓
Forensic Image
      ↓
Extracted Artifact
      ↓
Derived Intelligence
```

The current prototype starts from an already acquired forensic image.

The prototype does not create forensic images.

Potential input formats include E01/EWF and RAW, but supported formats must be verified experimentally in the target implementation.

Never assume forensic imaging reduces data size.

If acquisition or imaging is discussed, validate:

- Acquisition methodology
- Image format
- Storage
- Hashing
- Write protection
- Integrity
- Chain of custody
- Verification

---

## 6. Autopsy Integration

The first vertical slice should be:

```text
Upload
  ↓
Create / start analysis job
  ↓
Autopsy processing
  ↓
Observation complete
  ↓
Normalize evidence
  ↓
Display normalized results
```

Use asynchronous job handling.

Do not design the UI around sub-second forensic analysis.

The investigator should receive visible job state such as:

- Uploaded
- Queued
- Processing
- Extracting
- Normalizing
- Ready
- Failed

Autopsy capabilities should be treated according to verified documentation. Do not claim that it guarantees recovery of every deleted file.

Deleted/unallocated examination and data carving are different concepts.

Do not describe Plaso as an imaging tool. It is associated with timeline/artifact analysis.

Do not assume face recognition is an Autopsy capability. Face recognition belongs in the Processing layer unless separately verified.

---

## 7. Evidence Contract

Processing must not depend directly on internal Autopsy structures.

A normalized evidence object may contain:

```json
{
  "case_id": "...",
  "evidence_id": "...",
  "source_id": "...",
  "source_type": "forensic_image",
  "source_format": "E01",
  "source_path": "...",
  "file_name": "...",
  "file_type": "...",
  "size": 0,
  "deleted_status": "known",
  "timestamps": {},
  "hashes": {},
  "metadata": {},
  "artifacts": [],
  "relationships_observed": [],
  "timeline_events": [],
  "autopsy_reference": {},
  "provenance": {}
}
```

This is a conceptual contract. The implementation team should version it and refine fields based on actual Autopsy output and Processing requirements.

Every derived intelligence result should retain evidence provenance.

---

## 8. Processing Layer

Processing must remain modular.

Current planned workflows:

### A. Facial Recognition

Conceptual flow:

```text
Observed Image
    ↓
Face Detection
    ↓
Face Embedding
    ↓
Compare Against Synthetic FIR Image Dataset
    ↓
Similarity
    ↓
Potential Association
    ↓
Person / FIR
    ↓
Graph
```

Important constraints:

- Do not hard-code a particular embedding dimension.
- Do not hard-code YOLO or ResNet without benchmarking.
- Define a model-agnostic interface.
- Benchmark candidate models using the project dataset.
- Report similarity and confidence separately where appropriate.
- Preserve the source image and evidence reference behind every match.

The intended demonstration is synthetic:

- Synthetic FIR records contain person information and photographs.
- The same or controlled photographs are inserted into synthetic forensic evidence.
- The system identifies a potential match.
- The matched person becomes a graph node.
- The investigator can inspect the evidence supporting the association.

This is a demonstration workflow, not a claim of real-world forensic accuracy.

---

### B. Critical Contact / Network Analysis

The exact terminology should be validated with the project team. Prefer a defensible label such as:

**Critical Contact / Network Analysis**

Conceptual flow:

```text
Observed Contacts / Entities
        ↓
Relationship Identification
        ↓
Supporting Evidence
        ↓
Analytical Score
        ↓
Critical Contact Indicator
```

CCC thresholds are working assumptions only until validated experimentally.

Current conceptual thresholds:

- 0–40: lower confidence
- >40–80: moderate
- >80: higher confidence

Do not present these thresholds as scientifically validated.

---

### C. Network Analysis

Conceptual flow:

```text
Entities + Relationships + Scores
        ↓
Graph
        ↓
Centrality / Community / Path Analysis
        ↓
Investigator Visualization
```

Start with interpretable graph analytics.

Do not make Graph Neural Networks a mandatory first prototype component.

GNNs and advanced link prediction may be considered as future experimental work after baseline graph analytics are established.

---

### D. Linkage Explanation

This is a major product differentiator.

Conceptual flow:

```text
Analytical Result
      ↓
Supporting Signals
      ↓
Evidence References
      ↓
Human Verification
```

When an investigator clicks an edge, the system should answer:

**Why are these entities linked?**

Possible supporting signals include:

- Face similarity
- Calls
- Shared locations
- Vehicle association
- FIR references
- Timeline overlap
- Source evidence path
- Other verified artifact relationships

Never display an unexplained score when the system can provide evidence provenance.

---

## 9. Investigator Graph UI

The graph is not merely a visualization.

It is an evidence-explanation interface.

Preferred UI concept:

```text
                 GREEN
        ┌─────────────────────┐
        │                     │
        │       YELLOW        │
        │    ┌───────────┐    │
        │    │   RED     │    │
        │    │  TARGET   │    │
        │    └───────────┘    │
        │                     │
        └─────────────────────┘
```

The exact ring placement must be derived from an explicit scoring rule.

Do not assign colors arbitrarily.

Preferred graph interaction:

1. Central target node
2. Connected people/entities
3. Red / yellow / green zones
4. Visible relationships
5. Clickable nodes
6. Clickable edges
7. Explanation panel
8. Evidence provenance
9. FIR reference
10. Confidence
11. Human verification action
12. Legend explaining the scoring method

Cytoscape.js is the preferred initial frontend graph engine because its documented layouts include a concentric layout based on a user-defined metric.

D3.js may be evaluated if Cytoscape.js becomes insufficient.

---

## 10. Graph Database Selection

Do not select a graph database by reputation alone.

Candidates:

### Memgraph

Investigate:

- Cypher support
- Real-time analytics
- Centrality
- Community detection
- Link prediction
- Python integration
- Operational footprint
- Memory usage
- Deployment simplicity
- License

### FalkorDB

Investigate:

- OpenCypher support
- Graph representation
- Indexing
- Vector capabilities
- Python integration
- Docker deployment
- Memory usage
- License
- Query performance

### Neo4j

Investigate:

- Mature ecosystem
- Cypher
- Graph Data Science
- Centrality
- Community detection
- Similarity
- Path finding
- Link prediction
- Python integration
- Deployment model
- License
- Operational complexity

### Required Decision Rule

Benchmark all serious candidates using the same synthetic crime-network workload.

Example benchmark dataset:

- 1,000 people
- 5,000 phone numbers
- 2,000 vehicles
- 3,000 locations
- 10,000 events
- 20,000 relationships

Measure:

- Startup / readiness
- Memory
- CPU
- Insert throughput
- 1-hop traversal
- 2-hop traversal
- 3-hop traversal
- Shortest path
- Centrality
- Community detection
- Similarity / link prediction where supported
- Update latency
- Python API latency
- Frontend integration
- Setup complexity
- Reset simplicity
- License and deployment constraints

Do not use vendor claims as benchmark results.

Record versions, configuration, hardware, dataset size, query definitions and measured results.

After selection:

- Remove active runtime data and dependencies for rejected candidates where safe.
- Retain a compact benchmark report.
- Retain versions and configurations.
- Retain measurements.
- Retain the decision rationale.
- Never delete source synthetic data or benchmark evidence.

---

## 11. Synthetic Demonstration Dataset

The first demonstration should use synthetic data.

Do not assume access to confidential NCRB data.

The synthetic dataset should be able to demonstrate:

```text
Synthetic FIR
    ↓
Person
    ↓
Photo
    ↓
Potential Face Match
    ↓
Graph Node
    ↓
Phone / Vehicle / Location / Organization / Event Relationships
    ↓
Network Analysis
    ↓
Why Linked?
    ↓
Evidence
    ↓
Human Verification
```

Dataset documentation must identify:

- Dataset type
- Synthetic / demonstration status
- Format
- Fields
- Entities
- Relationships
- Volume
- Sensitivity
- Research value
- Limitations
- Generation method

---

## 12. Research Discipline

Before proposing implementation:

1. Determine what already exists.
2. Identify equivalent tools and capabilities.
3. Identify what is genuinely new.
4. Identify feasibility constraints.
5. Identify missing components.
6. Decide what should be built.
7. Explain why it matters.

Every important claim should be classified as:

- FACT
- VERIFIED
- VENDOR CLAIM
- INFERENCE
- PROPOSAL
- EXPERIMENTAL
- UNKNOWN

Never invent:

- Tools
- Features
- Versions
- Release dates
- Research papers
- URLs
- APIs
- Dataset availability
- NCRB capabilities

If evidence is unavailable, mark the item UNKNOWN and propose a verification experiment.

---

## 13. Feasibility Labels

Use:

- 🟢 Directly feasible
- 🟡 Feasible with constraints
- 🟠 Research-heavy
- 🔴 Not practical for current prototype

Evaluate:

- Compute
- Memory
- Storage
- Dataset availability
- API availability
- Development effort
- Deployment effort
- Scalability
- Demonstrability

Prefer features that can actually be demonstrated.

---

## 14. Antigravity Working Model

Antigravity should be treated as the primary development environment.

Use explicit project artifacts rather than relying on conversation memory.

Recommended repository structure:

```text
PROJECT_STATUS.md
ARCHITECTURE.md
RESEARCH/
BENCHMARKS/
OBSERVATION/
PROCESSING/
FRONTEND/
DATA/
DECISIONS/
TESTS/
```

Suggested decision records:

```text
DECISIONS/
  ADR-001-product-platform.md
  ADR-002-observation-engine.md
  ADR-003-evidence-contract.md
  ADR-004-graph-database.md
  ADR-005-graph-visualization.md
  ADR-006-face-model.md
```

Agents must update these documents when an architecture decision is actually validated.

Do not silently change architecture.

---

## 15. Antigravity Skills

For repeatable specialist behavior, prefer Agent Skills over large monolithic workflows.

Recommended future skill structure:

```text
.agents/
  skills/
    research-verification/
      SKILL.md
      references/
    graph-benchmark/
      SKILL.md
      scripts/
      references/
    forensic-observation/
      SKILL.md
      references/
    processing-pipeline/
      SKILL.md
      examples/
    architecture-review/
      SKILL.md
      references/
```

Each skill should have:

```yaml
---
name: skill-name
description: Clear description of when this skill should be used.
---
```

Keep each skill focused.

Do not create one giant skill that tries to do everything.

---

## 16. Agent Operating Rules

When modifying the repository:

### Before coding

- Read relevant project documents.
- Inspect existing code.
- Check current architecture.
- Search for existing implementations.
- Identify dependencies.
- State assumptions.
- Identify unknowns.

### Before adding a new technology

- Explain what problem it solves.
- Check whether an existing dependency already solves the problem.
- Verify current documentation.
- Check license.
- Check platform compatibility.
- Estimate operational cost.
- Define a benchmark if performance matters.

### Before changing architecture

Produce:

```text
Current
Proposed
Reason
Benefit
Tradeoff
Evidence
```

### Before declaring success

Run relevant tests.

Record:

- What was tested
- Test data
- Expected result
- Actual result
- Failure cases
- Limitations

Do not declare a feature complete merely because the code runs.

---

## 17. First Prototype Priority

Build the smallest end-to-end slice that proves the architecture:

```text
Upload Synthetic Forensic Image
        ↓
Autopsy Observation
        ↓
Normalized Evidence Contract
        ↓
Processing
        ↓
Synthetic Face Match
        ↓
Graph Node / Relationship
        ↓
Cytoscape.js Visualization
        ↓
Click Edge
        ↓
Why Are They Linked?
        ↓
Evidence References
        ↓
Human Verification
```

This vertical slice is more valuable than implementing many disconnected features.

---

## 18. What Must Not Be Done Prematurely

Do not:

- Build a full forensic imaging system first.
- Treat Autopsy as the product.
- Depend on undocumented Autopsy database internals.
- Claim universal deleted-file recovery.
- Claim face recognition without validated benchmarks.
- Hard-code an embedding dimension.
- Hard-code a face model without benchmarking.
- Make GNNs mandatory for the first prototype.
- Select a graph database without benchmarking.
- Treat graph database UI as the final investigator UI.
- Assign graph ring colors without a scoring rule.
- Claim access to confidential NCRB data without evidence.
- Present CCC thresholds as validated.
- Automatically label a person guilty or criminal.
- Add technologies simply because they are modern.

---

## 19. Required Agent Response Style

When reporting work, use this structure where applicable:

### Status

What was done.

### Evidence

What supports the decision.

### Decision

What is now accepted.

### Unknowns

What remains unverified.

### Risks

What could invalidate the approach.

### Next Action

The smallest useful next step.

Use concise, engineering-focused language.

---

## 20. Critical Review Requirement

The agent must actively challenge the project.

Ask:

- What already exists?
- Are we reinventing something?
- What are we missing?
- Can this actually work?
- Can we demonstrate it?
- What could invalidate the approach?
- What is the strongest alternative?
- What evidence would change the decision?

Agreement is not the goal.

Evidence-backed progress is the goal.

---

## 21. Current Strategic Direction

The current preferred direction is:

```text
Local Web Application
        ↓
React + TypeScript
        ↓
Cytoscape.js
        ↓
FastAPI
        ↓
Modular Processing
        ↓
Autopsy Observation
        ↓
Evidence Contract
        ↓
Benchmark-selected Graph Database
        ↓
Explainable Investigator Dashboard
```

The graph database choice remains OPEN until benchmarking.

The face recognition model choice remains OPEN until benchmarking.

The exact CCC formula and thresholds remain OPEN until validation.

The architecture should therefore use interfaces around these components.

---

## 22. Source Hierarchy

When researching, prioritize:

1. Official government sources
2. Official vendor documentation
3. Official GitHub repositories
4. Research papers
5. Technical DFIR sources
6. Professional communities
7. News and general web sources for discovery

For important claims, seek multiple independent sources.

---

## 23. Final Principle

Do not optimize for maximum technology.

Optimize for:

```text
Evidence
→
Explainability
→
Demonstrability
→
Validation
→
Investigator Value
```

Build only what can be justified, tested, demonstrated and explained.
