"""
Domain Models for Deep Artifact Parsing & Evidence Enrichment (Slice 8A).
Defines standardized models for parsed metadata, observations, and status flags.
Extracted data represents observed digital forensic evidence only, never speculative intelligence.
"""

from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field


class ParsingStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    UNSUPPORTED = "UNSUPPORTED"
    CORRUPTED = "CORRUPTED"
    OVERSIZED = "OVERSIZED"


class ParserType(str, Enum):
    PDF = "PDF"
    IMAGE = "IMAGE"
    SQLITE = "SQLITE"
    AUTOPSY_SQLITE = "AUTOPSY_SQLITE"
    UNSUPPORTED = "UNSUPPORTED"


class ObservationType(str, Enum):
    DOCUMENT_TEXT = "DOCUMENT_TEXT"
    DOCUMENT_METADATA = "DOCUMENT_METADATA"
    IMAGE_DIMENSIONS = "IMAGE_DIMENSIONS"
    IMAGE_EXIF = "IMAGE_EXIF"
    IMAGE_GPS = "IMAGE_GPS"
    SQLITE_SCHEMA = "SQLITE_SCHEMA"
    SQLITE_SAMPLE_ROWS = "SQLITE_SAMPLE_ROWS"
    SQLITE_STATS = "SQLITE_STATS"
    INTEGRITY_CHECK = "INTEGRITY_CHECK"
    FORENSIC_ACCOUNT = "FORENSIC_ACCOUNT"
    FORENSIC_COMMUNICATION = "FORENSIC_COMMUNICATION"
    FORENSIC_EMAIL_MESSAGE = "FORENSIC_EMAIL_MESSAGE"
    FORENSIC_EXIF_GPS = "FORENSIC_EXIF_GPS"
    FORENSIC_WEB_HISTORY = "FORENSIC_WEB_HISTORY"
    FORENSIC_WEB_COOKIE = "FORENSIC_WEB_COOKIE"
    FORENSIC_WEB_DOWNLOAD = "FORENSIC_WEB_DOWNLOAD"


class ExtractedObservation(BaseModel):
    """
    Individual digital observation extracted from an artifact.
    Preserves exact structural location (page number, table name, EXIF tag)
    and provenance. This is raw observed evidence, not graph intelligence.
    """
    observation_id: str
    observation_type: ObservationType
    location_reference: str  # e.g. "Page 1", "Table: users", "EXIF: GPSInfo"
    key: str
    value: Any
    confidence: float = 1.0  # 1.0 for deterministic digital forensic extractions
    provenance_note: Optional[str] = None


class ParserMetadata(BaseModel):
    parser_type: ParserType
    parser_name: str
    parser_version: str
    parsed_at: str
    execution_duration_ms: float
    file_size_bytes: int
    configured_size_ceiling_bytes: int


class ParsedArtifact(BaseModel):
    """
    Container for deeply inspected artifact observations and metadata.
    Enforces forensic integrity check between stored artifact hash and inspected bytes.
    """
    artifact_id: str
    case_id: str
    status: ParsingStatus
    parser_metadata: ParserMetadata
    computed_sha256: str
    integrity_verified: bool
    structured_metadata: Dict[str, Any] = Field(default_factory=dict)
    observations: List[ExtractedObservation] = Field(default_factory=list)
    error_message: Optional[str] = None
