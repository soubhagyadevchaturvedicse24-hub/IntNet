# Synthetic Forensic Ground-Truth Manifest Specification

**Document Version:** 1.0.0  
**Status:** `[PROPOSAL / SPECIFICATION]`  
**Date:** 2026-09-06  
**Target Fixture:** `SYN-IMAGE-01.E01` / `SYN-IMAGE-01.RAW` (5 GB Synthetic Forensic Disk Image)  

---

## 1. Forensic Fixture Lifecycle

To guarantee forensic integrity and experimental reproducibility, the synthetic benchmark disk image moves through a strictly enforced, unidirectional lifecycle:

```text
[1. GROUND-TRUTH SPECIFICATION]
               ↓
[2. FIXTURE GENERATION]
               ↓
[3. HASH & INTEGRITY VALIDATION]
               ↓
[4. IMMUTABLE FIXTURE STORAGE (Read-Only)]
               ↓
[5. BENCHMARK EXECUTION]
```

### Immutable Fixture Rule
Once the fixture generation script produces `SYN-IMAGE-01.E01` / `RAW` and records its master SHA-256 digest, the image is marked **read-only / write-protected**. Both Autopsy and IPED must process the exact same immutable binary file. The fixture must **never** be altered, updated, or rewritten between candidate benchmark runs.

---

## 2. Ground-Truth Manifest Artifact Inventory

The Ground-Truth Manifest (`SYN-FORENSIC-GROUND-TRUTH-V1`) specifies the exact, known contents built into the synthetic disk image against which candidate observations are evaluated.

### A. Filesystem & General File Metadata (Target: 270 Files)
* **Active Files:** 200 standard filesystem files (PDF, DOCX, TXT, JPG, DB).
* **Deleted Files:** 50 unallocated/deleted filesystem entries with preserved directory records.
* **Carved Files:** 20 orphaned media clusters without filesystem metadata.
* **Metadata Fields per File:**
  * Relative path within volume (e.g., `/data/media/0/DCIM/Camera/IMG_20260814_142011.jpg`).
  * File size in bytes.
  * Sector start and byte offset on disk (`byte_start`).
  * Cryptographic Hashes: MD5 and SHA-256.
  * Filesystem Timestamps: Created (`crtime`), Modified (`mtime`), Accessed (`atime`).

---

### B. Photographs & EXIF Metadata (Target: 200 Images)
* **Active Photos:** 150 JPEGs with complete EXIF headers.
* **Carved Photos:** 30 JPEGs carved from unallocated space.
* **Deleted Photos:** 20 JPEGs with deleted directory flags.
* **Ground-Truth EXIF Fields:**
  * Camera Make & Model (e.g., `Make: SyntheticPhone`, `Model: Pro-10`).
  * Capture Timestamp (`EXIF:DateTimeOriginal`).
  * GPS Location Fix: Latitude, Longitude, Altitude (e.g., `28.6139, 77.2090, 215.0m`).
  * Focal Length, Aperture, ISO settings.

---

### C. Mobile SQLite Databases (Target: 3 Core Databases)
1. **Contacts Database (`contacts2.db`):**
   * Target Volume: 50 contact entries.
   * Fields: Contact Name, Phone Numbers, Email Address, Last Updated Timestamp.
2. **Call Log Database (`calllog.db`):**
   * Target Volume: 120 call records.
   * Fields: Caller Number, Recipient Number, Call Direction (`INCOMING`/`OUTGOING`/`MISSED`), Call Timestamp, Duration in Seconds.
3. **SMS / Message Database (`mmssms.db`):**
   * Target Volume: 80 message threads.
   * Fields: Address, Timestamp, Message Body, Read/Sent Status.

---

### D. Distractor & Corruption Blocks (Target: 5 Files)
* 5 files containing deliberate header corruption or truncated sector blocks to evaluate candidate error handling and logging behavior.

---

## 3. Discrepancy & Artifact Loss Classification Standard

Candidate observation results are evaluated by comparing candidate outputs directly against this Ground-Truth Manifest. **No arbitrary percentage threshold (e.g., >5%) is used for automatic disqualification.**

Instead, every missing or inaccurate observation is recorded as a **Discrepancy** and evaluated using a three-part qualitative classification:

### A. Discrepancy Classification
* **Missing Observation:** An artifact present in the Ground-Truth Manifest was not extracted or reported by the candidate engine.
* **Inaccurate Metadata:** An artifact was extracted, but key attributes (e.g., EXIF coordinates, timestamps, hashes) differ from ground truth.
* **False Positive / Ghost Artifact:** An artifact was reported that does not exist in the Ground-Truth Manifest.
* **Provenance Breakage:** An artifact was extracted, but source path, byte offset, or hash provenance link back to the disk image is missing.

### B. Severity Levels
1. **Critical:** Failure to extract or accurately represent high-value investigative artifacts (e.g., missing call logs, corrupted GPS coordinates, dropped suspect photos).
2. **Major:** Failure to extract general filesystem metadata (e.g., missing access timestamps, unparsed file types).
3. **Minor:** Non-investigative metadata omissions (e.g., missing secondary EXIF camera settings like aperture or focal length).
4. **Informational:** Format presentation differences (e.g., ISO string formatting variations).

### C. Potential Decision Impact
Each discrepancy is assessed for its potential architectural impact:
* *Does this discrepancy invalidate the candidate's use for Crime Linkage decision support?*
* *Can the discrepancy be mitigated via custom ingest module configurations or normalizer post-processing?*

All discrepancy findings will be presented in the final benchmark report for human review and architectural decision making.
