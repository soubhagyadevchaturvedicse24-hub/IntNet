# Normalized Evidence Contract (v1.0.0) Specification

**Document Version:** 1.0.0  
**Status:** `[PROPOSAL]` (Baseline-aligned, awaiting validation against live Autopsy export)  
**Date:** 2026-09-05  
**Boundary Role:** Decoupling interface between **Observation Engine (Autopsy)** and **Processing / Graph / Dashboard Layers**.

---

## 1. Architectural Purpose & Contract Principle

The **Normalized Evidence Contract v1** defines the exact JSON schema emitted by the observation ingestion pipeline and consumed by downstream processing workflows.

### Core Design Rules
1. **Engine Agnostic:** Downstream processing pipelines (Face Matching, Entity Resolution, Graph Analytics) must never import Autopsy SDKs or execute direct SQL queries against Autopsy internal schemas.
2. **Minimal & Sufficient for Vertical Slice:** Contains only the fields strictly necessary to support the first vertical slice (Photo extraction $\rightarrow$ Face match against synthetic FIR $\rightarrow$ Graph node/edge creation $\rightarrow$ Cytoscape.js ring visualization $\rightarrow$ "Why Linked?" provenance inspection $\rightarrow$ Human verification).
3. **Strict Provenance Retention:** Every derived entity, face match, and relationship must retain an unbroken reference trail back to the physical source image, file path, offset, hash, and timestamp.

---

## 2. Evidence Contract Field Specification

### Envelope & Identification

| Field | Purpose | Req / Opt | Source | Status |
|---|---|---|---|---|
| `contract_version` | Schema version tracking (`"1.0.0"`). | **Required** | System Envelope | `[BASELINE]` |
| `case_id` | Unique identifier of the investigative case. | **Required** | System / Ingest Context | `[BASELINE]` |
| `evidence_id` | Unique UUID for this normalized evidence record. | **Required** | Normalizer Generator | `[BASELINE]` |
| `generated_at` | ISO 8601 timestamp of record normalization. | **Required** | Normalizer Generator | `[BASELINE]` |

---

### Source & Physical Provenance (`source`)

| Field | Purpose | Req / Opt | Source | Status |
|---|---|---|---|---|
| `source.source_id` | Unique ID of the original data source container. | **Required** | Autopsy Data Source ID | `[BASELINE]` |
| `source.source_type` | Type of container (`"forensic_image"`, `"logical_directory"`, `"raw_disk"`). | **Required** | Ingest Job Config | `[BASELINE]` |
| `source.source_format` | Format of source (`"E01"`, `"RAW"`, `"DD"`, `"DIRECTORY"`). | **Required** | Ingest Job Config | `[BASELINE]` |
| `source.source_path` | Absolute filesystem path of the original image/file. | **Required** | Ingest Job Config | `[BASELINE]` |
| `source.source_hashes` | Integrity hashes (`md5`, `sha256`) of the entire image. | **Optional** | Image Verification / Ingest | `[PROPOSAL]` |

---

### File & Artifact Metadata (`file_record`)

| Field | Purpose | Req / Opt | Source | Status |
|---|---|---|---|---|
| `file_record.file_name` | Name of the extracted/observed file. | **Required** | `tsk_files.name` / CASE-UCO | `[BASELINE]` |
| `file_record.file_path_in_source` | Full directory path within the image filesystem. | **Required** | `tsk_files.parent_path` | `[BASELINE]` |
| `file_record.file_size_bytes` | File size in bytes. | **Required** | `tsk_files.size` | `[BASELINE]` |
| `file_record.mime_type` | Detected MIME type (e.g., `"image/jpeg"`, `"text/csv"`). | **Required** | Autopsy File Type Analyzer | `[PROPOSAL]` |
| `file_record.deleted_status` | File status (`"active"`, `"deleted_recovered"`, `"carved"`). | **Required** | `tsk_files.dir_flags` | `[BASELINE]` |
| `file_record.byte_offset` | Physical byte offset on disk (if available). | **Optional** | `tsk_file_layout.byte_start` | `[UNKNOWN]` |
| `file_record.hashes.md5` | MD5 digest of file contents. | **Optional** | Autopsy Hash Lookup | `[BASELINE]` |
| `file_record.hashes.sha256` | SHA-256 digest of file contents. | **Required** | Autopsy Hash Lookup | `[BASELINE]` |
| `file_record.timestamps.created_at` | File creation timestamp (ISO 8601). | **Optional** | `tsk_files.crtime` | `[BASELINE]` |
| `file_record.timestamps.modified_at` | File last modified timestamp (ISO 8601). | **Required** | `tsk_files.mtime` | `[BASELINE]` |
| `file_record.timestamps.accessed_at` | File last accessed timestamp (ISO 8601). | **Optional** | `tsk_files.atime` | `[PROPOSAL]` |
| `file_record.timestamps.exif_captured_at` | Camera capture timestamp from EXIF header. | **Optional** | Autopsy EXIF Analyzer | `[PROPOSAL]` |

---

### Extracted Media & Artifact References (`extracted_artifacts[]`)

| Field | Purpose | Req / Opt | Source | Status |
|---|---|---|---|---|
| `artifact_id` | Unique ID of extracted artifact item. | **Required** | Normalizer Generator | `[BASELINE]` |
| `artifact_type` | Type: `"image_media"`, `"call_record"`, `"message"`, `"geo_location"`. | **Required** | Blackboard Artifact Type | `[BASELINE]` |
| `extracted_file_path` | Relative path to carved/extracted file on local disk. | **Optional** | `ModuleOutput/` directory | `[BASELINE]` |
| `attributes` | Key-value dictionary of artifact-specific attributes (e.g. GPS coordinates, call duration, phone numbers). | **Required** | `blackboard_attributes` | `[PROPOSAL]` |

---

### Extracted Entities & Relationships (`entities[]` & `relationships[]`)

| Field | Purpose | Req / Opt | Source | Status |
|---|---|---|---|---|
| `entities[].entity_id` | Temporary ID for entity within this evidence contract. | **Required** | Normalizer / Blackboard | `[BASELINE]` |
| `entities[].entity_type` | Type: `"Person"`, `"PhoneNumber"`, `"Vehicle"`, `"Location"`, `"Event"`. | **Required** | Parsed Artifact / Tag | `[BASELINE]` |
| `entities[].value` | Core identifier (e.g. phone number string, license plate, person name). | **Required** | Parsed Attribute Value | `[BASELINE]` |
| `entities[].confidence` | Extraction confidence (0.0 to 1.0). | **Required** | Extractor / Normalizer | `[PROPOSAL]` |
| `relationships[].source_entity_ref`| Reference to source entity ID. | **Required** | Relationship Builder | `[BASELINE]` |
| `relationships[].target_entity_ref`| Reference to target entity ID. | **Required** | Relationship Builder | `[BASELINE]` |
| `relationships[].relationship_type`| Semantic predicate (`"CALLED"`, `"ASSOCIATED_WITH"`, `"LOCATED_AT"`, `"APPEARS_IN"`). | **Required** | Relationship Builder | `[BASELINE]` |
| `relationships[].timestamp` | Timestamp of relationship occurrence (if applicable). | **Optional** | Artifact timestamp | `[PROPOSAL]` |

---

### Timeline Events (`timeline_events[]`)

| Field | Purpose | Req / Opt | Source | Status |
|---|---|---|---|---|
| `timeline_events[].event_id` | Unique event ID. | **Required** | Normalizer Generator | `[PROPOSAL]` |
| `timeline_events[].timestamp` | ISO 8601 timestamp of event. | **Required** | File/EXIF/Log time | `[BASELINE]` |
| `timeline_events[].event_type` | Classification (`"FILE_MODIFIED"`, `"CALL_MADE"`, `"PHOTO_CAPTURED"`, `"GEO_FIX"`). | **Required** | Artifact Type Mapping | `[PROPOSAL]` |
| `timeline_events[].description` | Human-readable event summary for investigator timeline. | **Required** | Normalizer Formatter | `[PROPOSAL]` |

---

### Observation Engine Traceability (`observation_provenance`)

| Field | Purpose | Req / Opt | Source | Status |
|---|---|---|---|---|
| `engine_name` | Name of observation tool (`"Autopsy"`). | **Required** | Observation Layer | `[BASELINE]` |
| `engine_version` | Version string of observation tool. | **Optional** | Observation Layer | `[PROPOSAL]` |
| `autopsy_object_id` | Native object ID in Autopsy (`obj_id` in `tsk_files`). | **Optional** | `tsk_files.obj_id` | `[PROPOSAL]` |
| `autopsy_artifact_id` | Native blackboard artifact ID (if parsed from blackboard). | **Optional** | `blackboard_artifacts.artifact_id` | `[PROPOSAL]` |

---

## 3. Synthetic JSON Contract Examples

### Example 1: Extracted Image Artifact (Photo with Face & EXIF Provenance)
*Use Case:* Vertical slice facial recognition and location provenance.

```json
{
  "contract_version": "1.0.0",
  "case_id": "CASE-2026-SYN-001",
  "evidence_id": "EV-IMG-90812",
  "generated_at": "2026-09-05T19:45:00Z",
  "source": {
    "source_id": "DS-001",
    "source_type": "forensic_image",
    "source_format": "E01",
    "source_path": "D:/Proto SIH/DATA/synthetic_phone_dump.e01",
    "source_hashes": {
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    }
  },
  "file_record": {
    "file_name": "IMG_20260814_142011.jpg",
    "file_path_in_source": "/data/media/0/DCIM/Camera/IMG_20260814_142011.jpg",
    "file_size_bytes": 2458912,
    "mime_type": "image/jpeg",
    "deleted_status": "active",
    "byte_offset": 104857600,
    "hashes": {
      "md5": "9e107d9d372bb6826bd81d3542a419d6",
      "sha256": "4c8996fb92427ae41e4649b934ca495991b7852b855e3b0c44298fc1c149afbf"
    },
    "timestamps": {
      "created_at": "2026-08-14T08:50:11Z",
      "modified_at": "2026-08-14T08:50:11Z",
      "exif_captured_at": "2026-08-14T08:50:10Z"
    }
  },
  "extracted_artifacts": [
    {
      "artifact_id": "ART-PHOTO-01",
      "artifact_type": "image_media",
      "extracted_file_path": "extracted/media/IMG_20260814_142011.jpg",
      "attributes": {
        "camera_make": "SyntheticPhone",
        "camera_model": "Pro-10",
        "gps_latitude": 28.6139,
        "gps_longitude": 77.2090,
        "altitude_meters": 215.0
      }
    }
  ],
  "entities": [
    {
      "entity_id": "ENT-LOC-01",
      "entity_type": "Location",
      "value": "28.6139,77.2090",
      "confidence": 0.95
    }
  ],
  "relationships": [],
  "timeline_events": [
    {
      "event_id": "EVT-001",
      "timestamp": "2026-08-14T08:50:10Z",
      "event_type": "PHOTO_CAPTURED",
      "description": "Photograph captured at coordinates (28.6139, 77.2090)"
    }
  ],
  "observation_provenance": {
    "engine_name": "Autopsy",
    "engine_version": "4.21.0",
    "autopsy_object_id": 14201,
    "autopsy_artifact_id": 89
  }
}
```

---

### Example 2: Communication Record (Call Log)
*Use Case:* Critical Contact / Network Linkage between two phone numbers.

```json
{
  "contract_version": "1.0.0",
  "case_id": "CASE-2026-SYN-001",
  "evidence_id": "EV-CALL-10293",
  "generated_at": "2026-09-05T19:45:00Z",
  "source": {
    "source_id": "DS-001",
    "source_type": "forensic_image",
    "source_format": "E01",
    "source_path": "D:/Proto SIH/DATA/synthetic_phone_dump.e01"
  },
  "file_record": {
    "file_name": "contacts2.db",
    "file_path_in_source": "/data/data/com.android.providers.contacts/databases/contacts2.db",
    "file_size_bytes": 524288,
    "mime_type": "application/vnd.sqlite3",
    "deleted_status": "active",
    "hashes": {
      "sha256": "8a3f5c6b9d2e1f4a7c0b3d5e8f1a4c7b0e3d6f9a2c5b8e1d4a7c0b3d5e8f1a4c"
    },
    "timestamps": {
      "modified_at": "2026-08-15T14:30:00Z"
    }
  },
  "extracted_artifacts": [
    {
      "artifact_id": "ART-CALLLOG-01",
      "artifact_type": "call_record",
      "attributes": {
        "call_direction": "OUTGOING",
        "caller_number": "+919876543210",
        "recipient_number": "+919123456780",
        "call_duration_seconds": 184,
        "call_status": "COMPLETED"
      }
    }
  ],
  "entities": [
    {
      "entity_id": "ENT-PH-01",
      "entity_type": "PhoneNumber",
      "value": "+919876543210",
      "confidence": 1.0
    },
    {
      "entity_id": "ENT-PH-02",
      "entity_type": "PhoneNumber",
      "value": "+919123456780",
      "confidence": 1.0
    }
  ],
  "relationships": [
    {
      "source_entity_ref": "ENT-PH-01",
      "target_entity_ref": "ENT-PH-02",
      "relationship_type": "CALLED",
      "timestamp": "2026-08-15T14:25:10Z"
    }
  ],
  "timeline_events": [
    {
      "event_id": "EVT-002",
      "timestamp": "2026-08-15T14:25:10Z",
      "event_type": "CALL_MADE",
      "description": "Outgoing call from +919876543210 to +919123456780 (Duration: 184s)"
    }
  ],
  "observation_provenance": {
    "engine_name": "Autopsy",
    "engine_version": "4.21.0",
    "autopsy_object_id": 8102,
    "autopsy_artifact_id": 312
  }
}
```

---

### Example 3: Geolocation Fix (Device Timeline Record)
*Use Case:* Shared location & timeline overlap detection.

```json
{
  "contract_version": "1.0.0",
  "case_id": "CASE-2026-SYN-001",
  "evidence_id": "EV-GEO-55412",
  "generated_at": "2026-09-05T19:45:00Z",
  "source": {
    "source_id": "DS-001",
    "source_type": "forensic_image",
    "source_format": "E01",
    "source_path": "D:/Proto SIH/DATA/synthetic_phone_dump.e01"
  },
  "file_record": {
    "file_name": "gservices.db",
    "file_path_in_source": "/data/system/users/0/gservices.db",
    "file_size_bytes": 1048576,
    "mime_type": "application/vnd.sqlite3",
    "deleted_status": "active",
    "hashes": {
      "sha256": "1f4a7c0b3d5e8f1a4c7b0e3d6f9a2c5b8e1d4a7c0b3d5e8f1a4c7b0e3d6f9a2c"
    },
    "timestamps": {
      "modified_at": "2026-08-14T11:00:00Z"
    }
  },
  "extracted_artifacts": [
    {
      "artifact_id": "ART-GEO-01",
      "artifact_type": "geo_location",
      "attributes": {
        "latitude": 28.6289,
        "longitude": 77.2065,
        "accuracy_radius_meters": 12.5,
        "source_app": "com.google.android.gms"
      }
    }
  ],
  "entities": [
    {
      "entity_id": "ENT-LOC-02",
      "entity_type": "Location",
      "value": "28.6289,77.2065",
      "confidence": 0.90
    }
  ],
  "relationships": [],
  "timeline_events": [
    {
      "event_id": "EVT-003",
      "timestamp": "2026-08-14T10:55:00Z",
      "event_type": "GEO_FIX",
      "description": "Location logged at (28.6289, 77.2065) within 12.5m accuracy"
    }
  ],
  "observation_provenance": {
    "engine_name": "Autopsy",
    "engine_version": "4.21.0",
    "autopsy_object_id": 9904,
    "autopsy_artifact_id": 418
  }
}
```

---

## 4. Downstream Layer Consumption Map

| Downstream Layer | Target Fields Consumed from Evidence Contract | Output Produced |
|---|---|---|
| **Facial Recognition** | `extracted_artifacts[type=image_media].extracted_file_path`, `file_record.hashes.sha256`, `evidence_id` | Face Embedding vector, Candidate match against synthetic FIR photo, Potential Association score. |
| **Entity Resolution** | `entities[].entity_type`, `entities[].value`, `file_record.timestamps` | Canonical Graph Nodes (Person, Phone, Location). |
| **Critical Contact / Network Analytics** | `relationships[type=CALLED]`, `timeline_events[]`, `attributes.call_duration_seconds` | Edge weights, CCC scoring, Concentric Ring placement (Red/Yellow/Green). |
| **Graph Database** | `entities[]`, `relationships[]`, `source.source_id`, `evidence_id` | Property Graph nodes, edges, Cypher queries. |
| **Investigator Dashboard ("Why Linked?")** | `file_record.file_path_in_source`, `file_record.hashes`, `file_record.timestamps`, `source.source_path`, `observation_provenance` | Interactive provenance inspector displaying exact supporting forensic source and confidence. |

---

## 5. Items Requiring Experimental Verification `[UNKNOWN]`

1. **Byte Offset Extraction (`file_record.byte_offset`):** Verify whether Autopsy's SQLite `tsk_file_layout` or CASE-UCO report exports raw byte start positions reliably for all image formats.
2. **Carved Media Path Stability:** Verify how Autopsy writes carved pictures to `ModuleOutput/` to ensure relative paths remain deterministic across multiple runs.
3. **Artifact Attribute Uniformity:** Verify attribute key naming conventions between Autopsy's Blackboard Attribute Types (`TSK_GEO_LATITUDE`, `TSK_PHONE_NUMBER`, etc.) and the contract normalizer dictionary.
