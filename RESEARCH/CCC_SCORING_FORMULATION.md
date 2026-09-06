# Critical Contact & Association (CCC) Scoring Formulation v1.0

**Status:** `[PROPOSED / OPEN]`  
**Document Classification:** Mathematical & Rule-Based Specification  
**Scope:** Phase 5 — CCC Scoring Formulation & Prioritization  

---

## 1. Objective & Analytical Purpose
The Critical Contact & Association (CCC) scoring model is a deterministic, explainable decision-support algorithm designed to help investigators prioritize relationships within complex forensic graphs.

CCC answers a single operational question:
> **"Which connections deserve investigator attention first, and why?"**

> [!IMPORTANT]
> **Responsible AI Boundary:** CCC is strictly a **working analytical score** representing relationship strength and evidence weight. It is **NOT** a probability of guilt, a criminal risk score, or an automated determination of wrongdoing.

---

## 2. Terminology Standard `[BASELINE]`
* **Association Score:** Integer range ($0 \text{ to } 100$) representing prioritized evidence strength.
* **Confidence:** Normalized multiplier ($0.0 \text{ to } 1.0$) reflecting entity match and provenance integrity.
* **Indicator:** An individual observed factor (e.g. recency, frequency, multi-source proof) contributing to the score.
* **Analytical Lead:** An association flagged for priority review by human investigators.
* **Potential Association:** A candidate edge requiring verification.
* **Supporting Evidence:** Evidence Contract IDs directly linked to the relationship.
* **Human Verification:** Investigator verification status (`VERIFIED`, `REJECTED`, `UNDER_REVIEW`).

---

## 3. Mathematical Formulation

The CCC Association Score ($S_{CCC}$) is calculated as a weighted sum of 6 explainable factors, scaled from $0$ to $100$:

$$S_{CCC} = \min\left(100, \text{Round}\left( \left( \sum_{i=1}^{6} W_i \times F_i \right) \times C_{ER} \times C_{Prov} \right)\right)$$

Where:
* $F_1$: **Relationship Type Base Weight** ($0 \text{ to } 1.0$)
* $F_2$: **Frequency Multiplier** ($0 \text{ to } 1.0$)
* $F_3$: **Recency Decay Factor** ($0 \text{ to } 1.0$)
* $F_4$: **Multi-Source Evidence Proof** ($0 \text{ to } 1.0$)
* $C_{ER}$: **Entity Resolution Match Confidence** ($0.5 \text{ to } 1.0$)
* $C_{Prov}$: **Evidence Provenance Quality** ($0.5 \text{ to } 1.0$)

---

## 4. Factors and Weight Rationale

| Factor | Name | Weight ($W_i$) | Score Range | Operational Rationale |
|---|---|---|---|---|
| **$F_1$** | **Relationship Base Type** | **25%** ($W_1 = 25$) | $0.20 - 1.00$ | Direct communication (`CALLED`) and shared asset usage (`USED_PHONE`, `USED_VEHICLE`) represent stronger primary links than passive spatial proximity. |
| **$F_2$** | **Interaction Frequency** | **20%** ($W_2 = 20$) | $0.10 - 1.00$ | Logarithmic scaling of interaction count ($N$). Repeated contacts ($N \ge 10$) indicate sustained association versus isolated one-off events. |
| **$F_3$** | **Observation Recency** | **20%** ($W_3 = 20$) | $0.10 - 1.00$ | Exponential time-decay based on days elapsed ($\Delta t$). Recent contacts ($\le 7\text{ days}$) carry higher immediate investigative utility. |
| **$F_4$** | **Multi-Source Confirmation** | **20%** ($W_4 = 20$) | $0.25 - 1.00$ | Number of independent forensic artifacts (e.g. Call Log + ANPR + FIR). Independent cross-validation significantly reduces false positives. |
| **$C_{ER}$** | **Entity Resolution Confidence** | Multiplier | $0.50 - 1.00$ | Scales overall score down if the underlying entity match is ambiguous (e.g. initial match `V. Singh`). |
| **$C_{Prov}$** | **Provenance Quality** | Multiplier | $0.50 - 1.00$ | Verifies cryptographic SHA-256 presence and sector offset integrity. Missing provenance reduces score confidence. |

---

## 5. Working Prioritization Thresholds `[EXPERIMENTAL]`

Concentric rings categorize relationships into working investigator queues:

```text
+-------------------------------------------------------------------+
|     RED RING (Association Score > 75)                             |
|     -> Highest-Priority Analytical Leads                           |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|     YELLOW RING (Association Score 41 – 75)                       |
|     -> Moderate-Priority Potential Associations                   |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|     GREEN RING (Association Score <= 40)                          |
|     -> Lower-Priority Contextual Connections                      |
+-------------------------------------------------------------------+
```

* **RED Ring ($S_{CCC} > 75$):** `WORKING / EXPERIMENTAL` — Highest-priority queue for immediate investigator inspection.
* **YELLOW Ring ($41 \le S_{CCC} \le 75$):** `WORKING / EXPERIMENTAL` — Moderate-priority queue.
* **GREEN Ring ($S_{CCC} \le 40$):** `WORKING / EXPERIMENTAL` — Background / low-priority contextual links.

---

## 6. Explainability Requirements
For every computed score, the system MUST emit a human-readable **Explanation Breakdown**:

```json
{
  "association_score": 78,
  "ring": "RED",
  "contributing_indicators": [
    "High Base Importance: Direct Voice Call (CALLED)",
    "High Interaction Frequency: 14 interactions recorded",
    "Recent Observation: Recorded 2 days ago",
    "Multi-Source Confirmation: Validated across 3 independent artifacts",
    "High ER Confidence: Exact entity match (100%)"
  ],
  "supporting_evidence_ids": [
    "EV-CONTRACT-2026-9001",
    "EV-CONTRACT-2026-9002",
    "EV-CONTRACT-2026-9003"
  ]
}
```
