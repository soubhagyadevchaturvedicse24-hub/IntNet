# Entity Resolution Specification v1.0

**Status:** `[PROPOSED / OPEN]`  
**Document Classification:** Architecture & Rule Specification  
**Scope:** Phase 3 — Entity Resolution Vertical Slice  

---

## 1. Objective
To specify an explainable, evidence-preserving Entity Resolution (ER) pipeline that normalizes raw observations extracted from forensic Evidence Contracts, evaluates candidate matches using rule-based and fuzzy metrics, resolves observations into canonical entities, and populates the Kùzu graph repository while maintaining 100% evidence provenance.

---

## 2. Terminology & Principles `[BASELINE]`
* **Candidate Match:** A pair of observations identified as potentially referring to the same real-world entity based on normalized similarity.
* **Potential Association:** A candidate link between entities subject to analytical review.
* **Match Confidence:** A normalized score ($0.0 \text{ to } 1.0$) representing identity likelihood based on deterministic rules or fuzzy distance metrics.
* **Supporting Evidence:** Source observation references (Evidence IDs, file paths, sector offsets, timestamps) attached to every canonical node and relationship.
* **Human Verification:** Operational state indicating whether an investigator has verified, rejected, or merged a candidate match.
* **Strict Safety Rule:** Entities are **never** labeled as "criminal" or "guilty". All classifications remain descriptive decision-support indicators.

---

## 3. Entity Scope
1. `Person`: (`name`, `fir_ref`, `aliases`, `dob_ref`)
2. `PhoneNumber`: (`number`, `carrier`, `country_code`)
3. `Vehicle`: (`license_plate`, `make`, `model`, `color`)
4. `Location`: (`location_id`, `latitude`, `longitude`, `zone`, `address`)
5. `Organization`: (`org_id`, `name`, `org_type`)

---

## 4. Resolution Pipeline Workflow

```text
+-------------------------------------------------------------------+
|              EVIDENCE CONTRACT (v1 JSON Observations)             |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                    RAW ENTITY EXTRACTION                          |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|               RULE-BASED NORMALIZATION ENGINE                     |
|  - Whitespace trim & single-space collapse                        |
|  - Case folding (UPPERCASE for plates/phones, Title for names)    |
|  - Phone E.164 standardization (+91 prefix handling)             |
|  - Vehicle registration stripping (removing spaces & dashes)     |
|  - Name punctuation & honorific cleaning                          |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                 CANDIDATE MATCHING ENGINE                         |
|  - Exact Normalized Match (Confidence = 1.00)                     |
|  - High-Confidence Fuzzy (Levenshtein/Jaro-Winkler >= 0.85)       |
|  - Ambiguous Candidate (Similarity 0.60 - 0.84) -> Human Review   |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|              CANONICAL ENTITY & RELATIONSHIP BUILDER              |
|  - Emits Canonical ID (e.g. CAN-PER-001)                          |
|  - Preserves array of source_evidence_ids                         |
|  - Preserves observed_values vs normalized_value                  |
|  - Preserves match_method and match_confidence                    |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|             KÙZU GRAPH REPOSITORY INTEGRATION                     |
|  - Ingests Canonical Nodes & Provenance Edges into Kùzu           |
+-------------------------------------------------------------------+
```

---

## 5. Provenance Schema Requirements
Every resolved canonical entity MUST retain:
* `canonical_entity_id`: Globally unique identifier (e.g. `CAN-PERSON-001`).
* `entity_type`: Target domain type (`Person`, `PhoneNumber`, `Vehicle`, `Location`, `Organization`).
* `canonical_name`: Preferred normalized representation.
* `observed_values`: List of raw strings extracted across observations.
* `source_evidence_ids`: List of Evidence Contract observation IDs.
* `match_confidence`: Float ($0.0 \text{ to } 1.0$).
* `match_method`: Rule identifier (e.g. `EXACT_NORMALIZED_PHONE`, `FUZZY_NAME_JARO_WINKLER`).
* `supporting_observations_count`: Integer count of merged evidence points.
