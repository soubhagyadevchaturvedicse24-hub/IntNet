"""
Artifact Domain Models & Taxonomy for CRIMENET (Slice 6).
Defines Layer 1 File/Artifact taxonomy, precise allocation and recovery status enums,
viewer recommendations, and API contract schemas.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ArtifactCategory(str, Enum):
    """Layer 1 File / Artifact Classification (Strictly separate from Layer 2 Intelligence Entities)."""
    DOCUMENT = "DOCUMENT"
    DATABASE = "DATABASE"
    IMAGE = "IMAGE"
    EMAIL = "EMAIL"
    LOG = "LOG"
    SPREADSHEET = "SPREADSHEET"
    MEDIA = "MEDIA"
    CDR = "CDR"
    FORENSIC_IMAGE = "FORENSIC_IMAGE"
    PARTITION_TABLE = "PARTITION_TABLE"
    RECOVERED_FILE = "RECOVERED_FILE"
    OTHER = "OTHER"


class AllocationStatus(str, Enum):
    """Precise filesystem allocation status."""
    ALLOCATED = "ALLOCATED"
    UNALLOCATED = "UNALLOCATED"
    DELETED = "DELETED"
    UNKNOWN = "UNKNOWN"


class RecoveryStatus(str, Enum):
    """Precise forensic file recovery status."""
    NONE = "NONE"
    RECOVERED = "RECOVERED"
    CARVED = "CARVED"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class ViewerType(str, Enum):
    """Recommended viewer interface for future frontend compatibility (does not execute viewers)."""
    IMAGE = "IMAGE"
    PDF = "PDF"
    SPREADSHEET = "SPREADSHEET"
    DATABASE = "DATABASE"
    TEXT = "TEXT"
    EMAIL = "EMAIL"
    MEDIA = "MEDIA"
    HEX = "HEX"
    UNSUPPORTED = "UNSUPPORTED"


class ProvenanceEnvelope(BaseModel):
    case_id: str
    evidence_id: str
    processing_job_id: str
    engine_name: str
    engine_version: str
    source_reference: str
    observation_reference: str


class Artifact(BaseModel):
    artifact_id: str
    case_id: str
    evidence_id: str
    processing_job_id: str
    filename: str
    path_within_source: str  # Path or offset inside source forensic image/evidence container
    category: ArtifactCategory = ArtifactCategory.OTHER
    mime_type: str = "application/octet-stream"
    file_extension: str = ""
    size_bytes: int = 0
    sha256: Optional[str] = None
    created_at_observed: Optional[str] = None
    modified_at_observed: Optional[str] = None
    accessed_at_observed: Optional[str] = None
    allocation_status: AllocationStatus = AllocationStatus.UNKNOWN
    recovery_status: RecoveryStatus = RecoveryStatus.UNKNOWN
    observation_method: str = "FILE_SYSTEM_PARSE"
    recommended_viewer: ViewerType = ViewerType.HEX
    provenance_chain: ProvenanceEnvelope
    content_reference: Optional[str] = None  # Server-controlled safe storage reference


class ArtifactResponse(BaseModel):
    artifact_id: str
    case_id: str
    evidence_id: str
    processing_job_id: str
    filename: str
    path_within_source: str
    category: ArtifactCategory
    mime_type: str
    file_extension: str
    size_bytes: int
    sha256: Optional[str] = None
    created_at_observed: Optional[str] = None
    modified_at_observed: Optional[str] = None
    accessed_at_observed: Optional[str] = None
    allocation_status: AllocationStatus
    recovery_status: RecoveryStatus
    observation_method: str
    recommended_viewer: ViewerType
    provenance_chain: ProvenanceEnvelope


class ArtifactFilterParams(BaseModel):
    category: Optional[ArtifactCategory] = None
    mime_type: Optional[str] = None
    filename: Optional[str] = None
    allocation_status: Optional[AllocationStatus] = None
    recovery_status: Optional[RecoveryStatus] = None
    evidence_id: Optional[str] = None
    processing_job_id: Optional[str] = None
