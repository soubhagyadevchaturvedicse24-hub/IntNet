# CRIMENET Prototype Demonstration Guide

**Version:** 1.0.0  
**Phase:** Final Prototype Baseline Demonstration  
**Target URL:** `http://localhost:8000/`  

---

## 1. How to Start the Application

Open a terminal in the project root directory (`d:/Proto SIH`) and run:

```bash
python -m uvicorn src.api.main:app --reload
```

* **Expected Server Output:**
  ```text
  INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
  ```
* Open a browser to `http://localhost:8000/` (or `http://127.0.0.1:8000/`).

---

## 2. Demonstration Data & Synthetic Fixture Summary

The demonstration relies on a 100% deterministic synthetic investigation scenario:

```text
RAW FORENSIC DISK IMAGE (SYN_REAL_FORENSIC_IMAGE.raw)
→ AUTOPSY / OBSERVATION NORMALIZER
→ EVIDENCE CONTRACT v1 JSON
→ RULE-BASED ENTITY RESOLUTION
→ KÙZU GRAPH REPOSITORY (BENCHMARKS/kuzu_resolved_graph_db)
→ CCC ASSOCIATION SCORING ENGINE
→ FASTAPI API & CYTOSCAPE.JS INVESTIGATOR UI
```

* **Target Suspect Entity:** `CAN-PER-0001` (Vikram Singh)
* **Associated Entities:**
  * `CAN-PER-0002` (Ananya Sharma) — Associated Person Lead
  * `CAN-PHO-0003` (`+919876543210`) — Shared Phone Asset
  * `CAN-VEH-0004` (`DL01AB1234`) — Shared Vehicle Asset
  * `CAN-LOC-0005` (`Connaught Place Zone 1`) — Visited Location Indicator

---

## 3. Exact Clicks & Demonstration Workflow

### Step 1: Open the Investigator Dashboard
* Navigate to `http://localhost:8000/`.
* **Observe:** The visual Cytoscape.js canvas loads automatically displaying the graph layout with color-coded nodes and edge priority rings (`RED`, `YELLOW`, `GREEN`).

### Step 2: Search / Select a Person
* In the top-left Search bar, type `CAN-PER-0001` and click **Search** (or click the amber node labeled `Vikram Singh (Person)` on the canvas).
* **Observe:** The right-hand **Inspector Panel** displays:
  * Canonical Entity ID: `CAN-PER-0001`
  * Entity Type: `Person`
  * Canonical Name: `Vikram Singh`
  * Observed Values: `Vikram Singh, Vikram  Singh, VIKRAM SINGH`
  * Match Confidence: `100%` (Exact Rule Match)
  * Human Verification Status: `UNDER_REVIEW` (or current status)

### Step 3: Show Connected Entities
* Observe the connected graph nodes linked to `Vikram Singh`:
  * `+919876543210` (`PhoneNumber`, Green Node)
  * `DL01AB1234` (`Vehicle`, Red Node)
  * `Connaught Place Zone 1` (`Location`, Purple Node)

### Step 4: Select an Important Relationship & Inspect CCC Score
* Click the relationship edge between `Vikram Singh` and `+919876543210` labeled `USED_PHONE [CCC: 98]`.
* **Observe:** The **CCC Relationship Inspector Panel** updates with:
  * **Association Score:** `98 / 100`
  * **Priority Ring:** `[RED RING]` (`Higher-Priority Analytical Lead`)
  * **Relationship Type:** `USED_PHONE`
  * **Interaction Frequency:** `15 interactions`
  * **Observation Recency:** `2.0 days ago`
  * **Independent Evidence Sources:** `3 artifacts`
  * **Entity Resolution Confidence:** `100%`
  * **Provenance Status:** `Verified Cryptographic SHA-256`
  * **Why Was This Score Assigned?** Displays factor breakdown list.

### Step 5: Evidence Traceability ("Why Does This Link Exist?")
* Look at the **Supporting Evidence Contract IDs** box inside the Relationship Inspector Panel.
* **Observe:**
  * Evidence Contract ID: `EV-CONTRACT-2026-9001`
  * Primary Source Artifact: `call_log.db` (`SQLite Database`)
  * Extracted Sector Path: `/data/data/com.android.providers.contacts/databases/calllog.db`
  * Cryptographic SHA-256: `466162a47a8058f081d96862c793e533fd92317e0347a0816ae23406722a7f33`
  * Timestamp: `2026-09-04T14:22:00Z`
  * Observation Details: `"Outgoing call from Vikram Singh to +919876543210. Duration: 145 seconds."`

### Step 6: Demonstrate Human Verification Logging
* At the bottom of the Inspector Panel, click **`[Verify Lead]`**.
* **Observe:** Alert confirms: `"Human Verification recorded as [HUMAN_VERIFIED_LEAD] for EDGE-0001"`. The status updates to `HUMAN_VERIFIED_LEAD`.
* Optionally click **`[Under Review]`** or **`[Reject]`** to demonstrate state changes (`UNDER_REVIEW`, `REJECTED_ASSOCIATION`).

---

## 4. How to Explain CCC & Responsible AI Boundaries

When presenting the CCC score to stakeholders, state clearly:

> "The Critical Contact & Association (CCC) score is an **experimental analytical prioritization score**, NOT a probability of guilt or criminal prediction. It prioritizes relationships for human investigator review using 4 deterministic factors: Relationship Base Importance, Interaction Frequency, Observation Recency, and Multi-Source Evidence Confirmation."

### Ring Terminology Rule:
* **RED Ring ($S_{CCC} > 75$):** *"Higher-Priority Analytical Lead"*
* **YELLOW Ring ($41 \le S_{CCC} \le 75$):** *"Moderate-Priority Potential Association"*
* **GREEN Ring ($S_{CCC} \le 40$):** *"Lower-Priority Contextual Connection"*

*Never use terms like 'criminal score', 'guilty person', or 'probability of crime'.*

---

## 5. Known Limitations & ADR Statuses

1. **Synthetic Fixture Baseline:** The evaluation datasets rely on synthetic FIR, phone, vehicle, and forensic image fixtures.
2. **Entity Resolution Accuracy:** The 1.0000 F1 score applies strictly to the 15-observation synthetic evaluation dataset, not general unconstrained real-world data.
3. **Working Thresholds:** CCC ring boundaries ($>75$, $41-75$, $\le 40$) are experimental working queues labeled as `WORKING / EXPERIMENTAL`.
4. **Architectural Decision Records:** All ADRs (`ADR-001` through `ADR-008`) remain explicitly marked **`[PROPOSED / OPEN]`**.
