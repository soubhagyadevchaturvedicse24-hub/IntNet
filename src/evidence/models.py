"""
Evidence Domain Models for CRIMENET (Slice 3).
Defines evidence types, preservation statuses, evidence entities, and API contract schemas.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    DISK_IMAGE = "DISK_IMAGE"
    LOGICAL_DUMP = "LOGICAL_DUMP"
    LOOSE_FILES = "LOOSE_FILES"
    MOBILE_EXTRACTION = "MOBILE_EXTRACTION"
    DOCUMENT = "DOCUMENT"


class PreservationStatus(str, Enum):
    PRESERVED = "PRESERVED"
    VERIFIED = "VERIFIED"
    CORRUPTED = "CORRUPTED"


class IntegrityStatus(str, Enum):
    INTACT = "INTACT"
    MISMATCH = "MISMATCH"


class Evidence(BaseModel):
    evidence_id: str
    case_id: str
    evidence_name: str
    evidence_type: EvidenceType
    original_filename: str
    original_size_bytes: int
    storage_reference: str
    sha256: str
    md5: Optional[str] = None
    registered_at: float
    registered_by: str  # user_id of registering officer
    source_description: Optional[str] = ""
    preservation_status: PreservationStatus = PreservationStatus.PRESERVED
    integrity_status: IntegrityStatus = IntegrityStatus.INTACT
    evidence_contract_ref: Optional[str] = None  # Reference ID to EvidenceContract_v1
    audit_references: List[str] = Field(default_factory=list)


class EvidenceCreate(BaseModel):
    evidence_name: str
    evidence_type: EvidenceType
    source_description: Optional[str] = ""


class EvidenceResponse(BaseModel):
    evidence_id: str
    case_id: str
    evidence_name: str
    evidence_type: EvidenceType
    original_filename: str
    original_size_bytes: int
    storage_reference: str
    sha256: str
    md5: Optional[str] = None
    registered_at: float
    registered_by: str
    source_description: Optional[str] = None
    preservation_status: PreservationStatus
    integrity_status: IntegrityStatus
    evidence_contract_ref: Optional[str] = None
    audit_references: List[str]


class EvidenceVerifyResponse(BaseModel):
    evidence_id: str
    case_id: str
    expected_sha256: str
    calculated_sha256: str
    integrity_status: IntegrityStatus
    verified_at: float
    verified_by: str
