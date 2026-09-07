"""
Processing Domain Models for CRIMENET (Slice 4).
Defines Processing Job statuses, entities, and API contract schemas.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ProcessingJob(BaseModel):
    job_id: str
    case_id: str
    evidence_id: str
    status: JobStatus = JobStatus.QUEUED
    engine_name: str
    engine_version: str
    image_format: str  # e.g., "RAW", "E01"
    observed_filesystem: Optional[str] = None  # e.g., "FAT32", "NTFS"
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    requested_by: str
    output_directory: str
    evidence_contract_ref: Optional[str] = None
    pre_processing_sha256: str
    post_processing_sha256: Optional[str] = None
    error_message: Optional[str] = None
    audit_references: List[str] = Field(default_factory=list)


class ProcessingJobCreate(BaseModel):
    engine_name: Optional[str] = "CRIMENET_RAW_OBSERVATION_ENGINE"


class ProcessingJobResponse(BaseModel):
    job_id: str
    case_id: str
    evidence_id: str
    status: JobStatus
    engine_name: str
    engine_version: str
    image_format: str
    observed_filesystem: Optional[str] = None
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    requested_by: str
    output_directory: str
    evidence_contract_ref: Optional[str] = None
    pre_processing_sha256: str
    post_processing_sha256: Optional[str] = None
    error_message: Optional[str] = None
    audit_references: List[str]
