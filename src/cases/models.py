"""
Case Domain Models for CRIMENET.
Defines case entities, statuses, judicial contexts, and request/response schemas.
"""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class CaseStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    UNDER_REVIEW = "UNDER_REVIEW"
    CLOSED = "CLOSED"


class AnchorRole(str, Enum):
    VICTIM = "Victim"
    INVESTIGATION_SUBJECT = "Investigation Subject"
    OTHER = "Other"


class CaseAnchor(BaseModel):
    anchor_id: str
    canonical_name: str
    role: AnchorRole = AnchorRole.INVESTIGATION_SUBJECT
    description: Optional[str] = None


class JudicialCaseContext(BaseModel):
    court_judge_id: Optional[str] = None
    court_level: str  # SPECIFIC_COURT, HIGH_COURT, SUPREME_COURT
    court_reference: Optional[str] = None
    judicial_case_reference: Optional[str] = None


class Case(BaseModel):
    case_id: str
    case_name: str
    description: str
    status: CaseStatus = CaseStatus.DRAFT
    created_by: str  # user_id of creator
    created_at: float
    updated_at: float
    judicial_context: Optional[JudicialCaseContext] = None
    assigned_investigators: List[str] = Field(default_factory=list)
    integrity_audit_references: List[str] = Field(default_factory=list)
    anchor: Optional[CaseAnchor] = None
    evidence_count: int = 0


class CaseCreate(BaseModel):
    case_name: str
    description: str
    judicial_context: Optional[JudicialCaseContext] = None
    assigned_investigators: List[str] = Field(default_factory=list)


class CaseUpdate(BaseModel):
    case_name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CaseStatus] = None
    judicial_context: Optional[JudicialCaseContext] = None
    assigned_investigators: Optional[List[str]] = None


class CaseResponse(BaseModel):
    case_id: str
    case_name: str
    description: str
    status: CaseStatus
    created_by: str
    created_at: float
    updated_at: float
    judicial_context: Optional[JudicialCaseContext] = None
    assigned_investigators: List[str]
    integrity_audit_references: List[str]
    anchor: Optional[CaseAnchor] = None
    evidence_count: int = 0
