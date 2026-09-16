"""
Domain Models for Forensic Signal & Relationship Extraction (Slice 8B).
Defines structured models for extracted signals, evidence-backed relationships,
and observation ingestion results.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ExtractedSignal(BaseModel):
    """
    Individual deterministic signal extracted from a deep parsed observation.
    Maintains exact forensic provenance back to the byte, page, or table row.
    """
    signal_id: str
    case_id: str
    evidence_id: str
    artifact_id: str
    observation_id: str
    job_id: str = ""
    entity_type: str  # "PhoneNumber", "Email", "Person", "Location", "Organization", "BankAccount"
    observed_value: str
    normalized_value: str
    source_location: str  # e.g. "Page 1", "Table: suspect_contacts, Row 3", "EXIF: GPSInfo"
    extraction_method: str  # e.g. "REGEX_PHONE_E164", "SQLITE_STRUCTURED_COLUMN", "EXIF_GPS_DMS"
    confidence: float = 1.0
    provenance_trace: str


class ExtractedRelationship(BaseModel):
    """
    Evidence-backed relationship extracted between two co-occurring or structurally linked signals.
    Never created from generic co-occurrence; requires explicit structural or contextual binding.
    """
    rel_id: str
    case_id: str
    evidence_id: str
    artifact_id: str
    observation_id: str
    job_id: str = ""
    source_signal_id: str
    target_signal_id: str
    source_canonical_id: Optional[str] = None
    target_canonical_id: Optional[str] = None
    source_label: str  # e.g. "Person", "PhoneNumber"
    target_label: str  # e.g. "PhoneNumber", "Location", "Person"
    rel_label: str  # e.g. "USED_PHONE", "CALLED", "ASSOCIATED_WITH", "LOCATED_AT", "TRANSFERRED_TO", "VISITED"
    source_location: str
    extraction_method: str
    confidence: float = 1.0
    human_verification_status: str = "UNDER_REVIEW"
    timestamp_observed: Optional[str] = None


class ObservationIngestResult(BaseModel):
    """
    Summary result emitted after processing parsed observations into canonical entities
    and evidence-backed relationships in the case knowledge graph.
    """
    status: str
    case_id: str
    artifacts_processed: int
    signals_extracted: int
    canonical_entities_created: int
    relationships_created: int
    canonical_entities: List[Dict[str, Any]] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
