# Autopsy CLI Verification & Ingestion Experiment Plan

**Document Version:** 1.0.0  
**Date:** 2026-09-05  
**Target Environment:** Windows 10/11 x64  
**Primary Reference:** Sleuth Kit Autopsy User Documentation — *Command Line Ingest & Reporting*

---

## 1. Purpose & Scope

The purpose of this verification plan is to experimentally test and document the capabilities, boundaries, and limitations of Autopsy's command-line automation on a Windows system.

This plan evaluates whether Autopsy can function as our decoupled **Observation / Examination Engine** without requiring manual UI operation by investigators during automated pipeline runs, and whether it can supply the data needed for our **Normalized Evidence Contract**.

---

## 2. Evidence Classification Standard

Every test and assertion in this document is labeled using the following standard:
* **`[VERIFIED]`** — Directly tested and confirmed on the local target environment, or explicitly confirmed by official vendor documentation.
* **`[UNKNOWN]`** — Unverified on local installation; behavior requires empirical testing.
* **`[EXPERIMENTAL]`** — Hypothesis or procedure currently scheduled for testing and measurement.

---

## 3. Official Autopsy Baseline & Architecture Findings

Based on official Sleuth Kit / Autopsy technical documentation:

1. **CLI Ingestion Command:**  
   Autopsy provides an automated ingestion invocation:
   ```cmd
   autopsy64.exe --inputPath="<IMAGE_PATH>" --caseName="<CASE_NAME>" --runFromCommandLine=true
   ```
   * *Documented Behavior:* Creates a case folder named `<caseName>_<timestamp>` in the output directory pre-configured in Autopsy options.
2. **UI Dependency:**  
   Official documentation explicitly notes that `--runFromCommandLine=true` launches the Autopsy UI during execution to coordinate ingest modules. Completely headless (no-window) execution is not guaranteed in standard Autopsy standalone distribution on Windows.
3. **Artifact Exposure Channels:**  
   Autopsy produces multiple output structures:
   * **Case SQLite Database (`autopsy.db`):** Contains structured tables including `tsk_files`, `blackboard_artifacts`, `blackboard_attributes`, and `data_source_info`.
   * **Automated Reports:** Autopsy can generate reports upon ingest completion, including **CASE-UCO** (JSON format based on the Unified Cyber Ontology) and HTML/XML summaries.
   * **Extracted Files Directory (`ModuleOutput/`):** Contains extracted pictures, carved files, and thumbnails.

---

## 4. Test Matrix & Experimental Protocols

### Summary Table

| # | Test Area | Category | Target Capability |
|---|---|---|---|
| T1 | Image Format Support | `[UNKNOWN]` | Accept E01 (Expert Witness Format) and RAW (dd) images via CLI. |
| T2 | Case Creation & Pathing | `[UNKNOWN]` | Automatically create isolated case directory with timestamping. |
| T3 | Automated Ingest Execution | `[UNKNOWN]` | Trigger end-to-end ingest upon process launch without blocking prompts. |
| T4 | Ingest Module Selection | `[UNKNOWN]` | Configure and run specific modules (Picture Analyzer, Hash, EXIF, Carving). |
| T5 | Processing Status Monitoring | `[UNKNOWN]` | Detect execution state (`Processing` vs `Completed` vs `Failed`) from external process. |
| T6 | Interactive UI Interference | `[UNKNOWN]` | Run without modal dialogs or human intervention blockers. |
| T7 | Metadata & Artifact Extraction | `[UNKNOWN]` | Extract required artifacts via CASE-UCO JSON / `autopsy.db` SQLite parser. |
| T8 | Provenance Preservation | `[UNKNOWN]` | Retain source image path, file offset, hash, and timestamp back to source. |

---

### Detailed Test Specifications

#### Test 1: E01 & RAW Forensic Image Ingestion
* **Objective:** Determine whether Autopsy CLI accepts standard E01 and RAW forensic images as `--inputPath` arguments.
* **Method:**
  1. Prepare a synthetic E01 image and a synthetic RAW (.raw / .dd) image.
  2. Execute:
     ```cmd
     autopsy64.exe --inputPath="D:\Proto SIH\DATA\synthetic_sample.e01" --caseName="test_case_e01" --runFromCommandLine=true
     ```
  3. Inspect if the data source is successfully mounted and analyzed.
* **Expected Result:** Autopsy adds the image data source without format errors.
* **Actual Result:** `[UNKNOWN]` — Pending local execution.
* **Evidence:** SleuthKit Docs state `--inputPath` accepts disk images and logical files.
* **Status:** `[EXPERIMENTAL]`

---

#### Test 2: Case Directory & Database Creation
* **Objective:** Determine how Autopsy creates case directories, database files, and file system permissions.
* **Method:**
  1. Configure output directory to `D:\Proto SIH\DATA\autopsy_cases`.
  2. Run CLI ingest with `--caseName="verify_case_001"`.
  3. Verify directory creation, naming convention (`verify_case_001_<timestamp>`), and presence of `autopsy.db`.
* **Expected Result:** Target directory is created containing `autopsy.db` SQLite database.
* **Actual Result:** `[UNKNOWN]` — Pending local execution.
* **Evidence:** Documented in SleuthKit User Guide (Command Line Ingest section).
* **Status:** `[EXPERIMENTAL]`

---

#### Test 3: Unattended Automated Ingest Execution
* **Objective:** Verify that ingest starts automatically without requiring a human operator to click "Next" or "Finish" in a wizard.
* **Method:**
  1. Trigger CLI ingest from a background PowerShell process.
  2. Monitor CPU / Disk activity and log outputs.
* **Expected Result:** Ingest pipeline starts immediately upon process launch.
* **Actual Result:** `[UNKNOWN]` — Pending local execution.
* **Evidence:** Official docs indicate `--runFromCommandLine=true` triggers automated ingest.
* **Status:** `[EXPERIMENTAL]`

---

#### Test 4: Ingest Module Profile Configuration
* **Objective:** Determine whether we can select a subset of ingest modules (e.g., Picture Analyzer, EXIF parser, Hash Lookup) to avoid unnecessary processing overhead (e.g., indexing unallocated space if not needed).
* **Method:**
  1. Create an Ingest Profile in Autopsy GUI (`Tools -> Options -> Ingest Options`).
  2. Assign the profile in the `Command Line Ingest` tab.
  3. Run CLI ingest and verify that only configured modules executed (inspect `autopsy.db` blackboard artifacts).
* **Expected Result:** Only selected modules run, reducing execution time.
* **Actual Result:** `[UNKNOWN]` — Pending local execution.
* **Evidence:** SleuthKit docs document GUI configuration of CLI ingest module settings.
* **Status:** `[EXPERIMENTAL]`

---

#### Test 5: Lifecycle & Completion Status Detection
* **Objective:** Establish how our backend service (FastAPI) can reliably detect when Autopsy has finished processing.
* **Method:**
  1. Test three candidate completion signals:
     * *Signal A (Process Exit):* Does `autopsy64.exe` terminate automatically when ingest completes?
     * *Signal B (Report Generation):* Does the presence of a generated report file signal completion?
     * *Signal C (Database Lock Release / Status Table):* Is `autopsy.db` write lock released, or does a status table indicate completion?
* **Expected Result:** At least one deterministic completion signal is available for automated polling.
* **Actual Result:** `[UNKNOWN]` — Pending local execution.
* **Evidence:** Unverified in official docs (GUI may remain open after CLI ingest completes).
* **Status:** `[EXPERIMENTAL]`

---

#### Test 6: UI Non-Interference & Headless Feasibility
* **Objective:** Verify whether Autopsy window opening interferes with background server execution or causes blocking modal error dialogs if an invalid file is provided.
* **Method:**
  1. Execute CLI ingest with a valid image.
  2. Execute CLI ingest with an invalid / corrupted path.
  3. Observe window behavior, focus stealing, and error dialog behavior.
* **Expected Result:** Process does not hang waiting for user clicks on error modals.
* **Actual Result:** `[UNKNOWN]` — Pending local execution.
* **Evidence:** SleuthKit docs state UI will open during CLI ingest.
* **Status:** `[EXPERIMENTAL]`

---

#### Test 7: Artifact & Metadata Extraction for Evidence Contract
* **Objective:** Verify which extraction mechanism is cleanest for populating the `EvidenceContract_v1`:
  * *Option A:* Parsing the generated **CASE-UCO JSON report**.
  * *Option B:* Directly querying the case SQLite database (`autopsy.db` tables: `tsk_files`, `blackboard_artifacts`, `blackboard_attributes`).
* **Method:**
  1. Ingest a synthetic disk image containing photos with EXIF metadata, contact lists, and call logs.
  2. Generate CASE-UCO report and inspect JSON structure.
  3. Query `autopsy.db` for corresponding artifact rows.
  4. Compare latency, completeness, and maintainability of Option A vs Option B.
* **Expected Result:** Either CASE-UCO JSON or SQLite queries provide full extraction of file hashes, EXIF dates, extracted faces/pictures, and device metadata.
* **Actual Result:** `[UNKNOWN]` — Pending local execution.
* **Evidence:** CASE-UCO and SQLite are official Autopsy features; parsing ergonomics must be validated.
* **Status:** `[EXPERIMENTAL]`

---

#### Test 8: Evidence Provenance Preservation
* **Objective:** Verify that extracted artifacts maintain an unbroken chain of custody and provenance back to the source image.
* **Method:**
  1. Verify that every extracted artifact record in `autopsy.db` / CASE-UCO contains:
     * Source Data Source ID / Image Path
     * File system path within image
     * Byte offset / sector location (where applicable)
     * MD5 / SHA-256 hash
     * File system creation / modification / access timestamps
* **Expected Result:** Complete provenance metadata is available for attachment to graph nodes and edges.
* **Actual Result:** `[UNKNOWN]` — Pending local execution.
* **Evidence:** SleuthKit `tsk_files` and blackboard architecture inherently store source object IDs.
* **Status:** `[EXPERIMENTAL]`

---

## 5. Feasibility Evaluation: Observation → Evidence Contract Boundary

### Feasibility Assessment: 🟡 Feasible with Constraints

* **Decoupling Feasibility:** High. Because Autopsy outputs both a standardized CASE-UCO JSON report and a standard SQLite database (`autopsy.db`), a lightweight Python Normalizer module can convert Autopsy's raw output into our `EvidenceContract_v1` without our core processing layer ever knowing about Autopsy internals.
* **Constraints Identified:**
  1. **UI Execution on Windows:** Autopsy CLI opens a GUI window during analysis; backend must run it as an asynchronous detached background process.
  2. **Completion Signaling:** If the Autopsy GUI process does not terminate automatically upon ingest completion, the backend normalizer must monitor the file system (e.g., file lock release or report file creation) rather than relying solely on process return codes.
  3. **Configuration Pre-requisite:** Ingest module profiles must be configured once via Autopsy GUI options before running unattended CLI commands.

---

## 6. Verification Protocol Execution Guide

When local Autopsy environment is available:

```powershell
# Step 1: Verify Autopsy executable path
$autopsyBin = "C:\Program Files\Autopsy-*\bin\autopsy64.exe"

# Step 2: Prepare test output directory
$outDir = "D:\Proto SIH\DATA\autopsy_output"
New-Item -ItemType Directory -Force -Path $outDir

# Step 3: Run Test Ingestion
& $autopsyBin --inputPath="D:\Proto SIH\DATA\synthetic_sample.e01" --caseName="cli_verification_test" --runFromCommandLine=true

# Step 4: Validate generated artifacts in output case directory
Get-ChildItem -Path "$outDir\cli_verification_test*" -Recurse
```
