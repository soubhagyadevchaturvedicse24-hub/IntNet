# CRIMENET INTELLIGENCE LAB
## SLICE 8A — PARSER VALIDATION REPORT: REAL EVIDENCE & SYNTHETIC BENCHMARK

**Benchmark Timestamp:** 2026-09-07T02:25:00+05:30  
**Overall Status:** SUCCESS (100% Verified)  
**Classification Standard:** FACT / VERIFIED / SYNTHETIC TEST DATA  

---

### 1. Mandatory Evaluation Question & Explicit Answer

> **Question:** *"Does the current system now parse real artifacts from the real E01/E02 evidence, or only demonstrate parser capability on synthetic artifacts?"*

**Formal Engineering Answer:**
**THE SYSTEM PARSES REAL ARTIFACTS EXTRACTED FROM THE REAL E01/E02 EVIDENCE FOR BOTH PDF DOCUMENTS AND IMAGES, WHILE USING CONTROLLED TEST DATA EXCLUSIVELY FOR SQLITE DATABASES DUE TO THE EMPIRICAL ABSENCE OF SQLITE CONTAINERS WITHIN THIS SPECIFIC FORENSIC IMAGE.**

- **Real E01 Artifacts Parsed (`FACT` / `VERIFIED`):**
  - Real PDF Document (Large): `Jeevan Setu.pdf` (8.3 MB, 33 pages) extracted from `Images_Set_1.E01`
  - Real PDF Document: `Crime Linkage Detector Meeting Minutes.pdf` (248 KB, 17 pages) extracted from `Images_Set_1.E01`
  - Real PNG Image (High-Res): `Golden Temple Aarti Ceremony.png` (2.54 MB, 1701x924 px) extracted from `Images_Set_1.E01`
  - Real PNG Image: `ChatGPT Image Aug 31, 2026.png` (2.58 MB, 1024x1536 px) extracted from `Images_Set_1.E01`
- **Synthetic Data Exclusively for Missing Type (`SYNTHETIC TEST DATA`):**
  - Controlled SQLite Database: `synthetic_sample.db` (16 KB, 3 tables, 25 rows)
  - **Reason for Synthetic Usage:** The NTFS logical volume in `Images_Set_1.E01` contains zero `.db` or `.sqlite` files across its 2,898 files and 1,122 directories. Rather than fabricating an image or pretending an artifact came from the E01 container, the test suite uses a dedicated test fixture explicitly labeled `SYNTHETIC TEST DATA`.

---

### 2. Forensic Image Immutability Audit

Before and after deep parsing execution, the SHA-256 fingerprints of the original FTK forensic images were computed in 4 MB streaming chunks:

| Forensic Container | File Location | Baseline SHA-256 Hash | Post-Validation SHA-256 Hash | Result |
|---|---|---|---|---|
| `Images_Set_1.E01` | `D:\Proto SIH\Images\` | `733948eee283af8e0dc9c6e389039569a41c4522172e8cdfcebf34e86f1cd21a` | `733948eee283af8e0dc9c6e389039569a41c4522172e8cdfcebf34e86f1cd21a` | ✅ 100% BIT-FOR-BIT IDENTICAL |
| `Images_Set_1.E02` | `D:\Proto SIH\Images\` | `1da71529a72d2e10e060efe900616f098691c65787ada11c95cefed7f8e0f84d` | `1da71529a72d2e10e060efe900616f098691c65787ada11c95cefed7f8e0f84d` | ✅ 100% BIT-FOR-BIT IDENTICAL |

**Zero Bytes Modified:** The deep parsing subsystem operates in strictly non-destructive read-only mode (`rb` and `file:...?mode=ro`). Original evidence remains forensically pure.

---

### 3. Empirical Parser Benchmark Metrics

Validation was executed via `BENCHMARKS/run_slice_8a_validation.py`. The empirical metrics are recorded below:

#### 3.1 Real PDF Artifact Benchmarks

##### A. Large PDF Document: `Jeevan Setu.pdf`
- **Artifact ID:** `ART-2026-001-1E6EA53D`
- **Provenance Trace:** `EV-2026-8A41_Images_Set_1.E01:/Chrome/Jeevan Setu.pdf`
- **File Size:** 8,298,577 bytes (~8.3 MB)
- **Parser Engine:** `CRIMENET_PDF_OBSERVATION_PARSER` v1.0.0
- **Execution Duration:** 660.92 ms
- **Throughput:** ~12.55 MB/s
- **Status:** `SUCCESS`
- **SHA-256 Verification:** `True` (Matched `1e6ea53d82f0e8aa2e6122fd5f3d2038757b5fc88d8dd6a1a8cba93f020d18c1`)
- **Extracted Metadata:**
  - `total_pages`: 33
  - `pages_inspected`: 20 (bounded by prototype safety ceiling)
  - `total_words_extracted`: 2,159 words
  - `is_encrypted`: False
- **Observations Generated:** 20 page text observation records with exact structural location tags (`Page 1 of 33`, etc.) and character count bounds.

##### B. Document: `Crime Linkage Detector Meeting Minutes.pdf`
- **Artifact ID:** `ART-2026-001-DAE9A00F`
- **Provenance Trace:** `EV-2026-8A41_Images_Set_1.E01:/Chrome/Crime Linkage Detector Meeting Minutes.pdf`
- **File Size:** 248,516 bytes (~248.5 KB)
- **Parser Engine:** `CRIMENET_PDF_OBSERVATION_PARSER` v1.0.0
- **Execution Duration:** 501.10 ms
- **Status:** `SUCCESS`
- **SHA-256 Verification:** `True` (Matched `dae9a00fb193c3939286f77183e2b7e7c2d123bc159e4d4db33fc5591f8d7132`)
- **Extracted Metadata:**
  - `total_pages`: 17
  - `pages_inspected`: 17
  - `total_words_extracted`: 2,344 words
- **Observations Generated:** 21 records (including Document Information Dictionary metadata and 17 page text chunks).

---

#### 3.2 Real Image Artifact Benchmarks

##### A. High-Resolution PNG: `Golden Temple Aarti Ceremony.png`
- **Artifact ID:** `ART-2026-001-48A024E4`
- **Provenance Trace:** `EV-2026-8A41_Images_Set_1.E01:/Chrome/Golden Temple Aarti Ceremony.png`
- **File Size:** 2,544,344 bytes (~2.54 MB)
- **Parser Engine:** `CRIMENET_IMAGE_EXIF_PARSER` v1.0.0
- **Execution Duration:** 91.65 ms
- **Throughput:** ~27.76 MB/s
- **Status:** `SUCCESS`
- **SHA-256 Verification:** `True` (Matched `48a024e4dfe86684220dead8af15cee9251082094eafac295e7e1450682ca5e2`)
- **Extracted Metadata:**
  - `dimensions`: 1701 &times; 924 pixels
  - `aspect_ratio`: 1.841
  - `format`: PNG
  - `color_mode`: RGB
  - `exif_tags`: 0 (clean PNG image, no device header tags)
  - `has_gps`: False
- **Observations Generated:** 2 records (dimensions and format/color-mode).

##### B. Generated Image: `ChatGPT Image Aug 31, 2026, 07_25_22 PM.png`
- **Artifact ID:** `ART-2026-001-57103AF2`
- **Provenance Trace:** `EV-2026-8A41_Images_Set_1.E01:/Chrome/ChatGPT Image Aug 31, 2026, 07_25_22 PM.png`
- **File Size:** 2,584,338 bytes (~2.58 MB)
- **Parser Engine:** `CRIMENET_IMAGE_EXIF_PARSER` v1.0.0
- **Execution Duration:** 61.30 ms
- **Status:** `SUCCESS`
- **SHA-256 Verification:** `True` (Matched `57103af20fab80c58acd526ab61e7fcbe84428793d72b65bebf59da30a94848a`)
- **Extracted Metadata:**
  - `dimensions`: 1024 &times; 1536 pixels
  - `format`: PNG
  - `color_mode`: RGB
- **Observations Generated:** 2 records.

---

#### 3.3 Synthetic SQLite Database Benchmark

- **Artifact File:** `DATA/test_fixtures/synthetic_sample.db`
- **Classification:** `SYNTHETIC TEST DATA` (Controlled Test Fixture)
- **File Size:** 16,384 bytes
- **Parser Engine:** `CRIMENET_SQLITE_FORENSIC_PARSER` v1.0.0
- **Execution Duration:** 5.75 ms
- **Status:** `SUCCESS`
- **Introspected PRAGMAs:**
  - `page_size`: 4,096 bytes
  - `encoding`: `UTF-8`
  - `user_version`: 8
  - `freelist_count`: 0
- **Discovered Tables & Bounded Observations:**
  1. `suspect_contacts`:
     - Discovered Columns: `id (INTEGER)`, `name (TEXT)`, `phone (TEXT)`, `role (TEXT)`
     - Total Rows: 25 rows
     - Bounded Count Display: `25` (Exact count; under 10,000 threshold)
     - Returned Sample Records: Strictly 10 sample rows (capped at limit)
  2. `system_logs`:
     - Discovered Columns: `log_id (INTEGER)`, `timestamp (TEXT)`, `event_type (TEXT)`, `details (TEXT)`
     - Total Rows: 15 rows
     - Returned Sample Records: Strictly 10 sample rows
  3. `metadata_tags`:
     - Discovered Columns: `tag_id (INTEGER)`, `tag_name (TEXT)`
     - Total Rows: 3 rows
     - Returned Sample Records: 3 sample rows

---

### 4. Summary Matrix of Tested Artifacts

| Artifact Name | Data Source | Type | File Size | Execution Time | SHA-256 Match | Observations Extracted | Status |
|---|---|---|---|---|---|---|---|
| `Jeevan Setu.pdf` | Real E01 (NTFS) | PDF | 8,298,577 B | 660.92 ms | ✅ True | 20 | `SUCCESS` |
| `Meeting Minutes.pdf` | Real E01 (NTFS) | PDF | 248,516 B | 501.10 ms | ✅ True | 21 | `SUCCESS` |
| `Golden Temple.png` | Real E01 (NTFS) | IMAGE | 2,544,344 B | 91.65 ms | ✅ True | 2 | `SUCCESS` |
| `ChatGPT Image.png` | Real E01 (NTFS) | IMAGE | 2,584,338 B | 61.30 ms | ✅ True | 2 | `SUCCESS` |
| `synthetic_sample.db` | Controlled Fixture | SQLITE | 16,384 B | 5.75 ms | ✅ True | 7 | `SUCCESS` |
| `spoofed_fake.pdf` | Security Fixture | FAKE | 37 B | < 1 ms | N/A | 0 | `UNSUPPORTED` |
| `spoofed_fake.png` | Security Fixture | FAKE | 30 B | < 1 ms | N/A | 0 | `UNSUPPORTED` |
| `spoofed_fake.db` | Security Fixture | FAKE | 31 B | < 1 ms | N/A | 0 | `UNSUPPORTED` |
| `corrupt.pdf` | Security Fixture | CORRUPT | 33 B | < 2 ms | N/A | 0 | `FAILED` |
