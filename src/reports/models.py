"""
Pydantic Data Models for CRIMENET Report Subsystem.
Defines versioning, source scope, cryptographic integrity, and report schemas.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ReportTemplateType(str, Enum):
    COMPREHENSIVE_DOSSIER = "COMPREHENSIVE_DOSSIER"
    EXECUTIVE_BRIEF = "EXECUTIVE_BRIEF"
    SECTION_65B_DRAFT = "SECTION_65B_DRAFT"
    NETWORK_LINKAGE = "NETWORK_LINKAGE"


class ReportStatus(str, Enum):
    SYSTEM_GENERATED = "SYSTEM_GENERATED"
    EXAMINER_REVIEW = "EXAMINER_REVIEW"
    FINALIZED = "FINALIZED"


class ReportGenerateRequest(BaseModel):
    template_type: ReportTemplateType = Field(default=ReportTemplateType.COMPREHENSIVE_DOSSIER)
    title: Optional[str] = Field(default=None, description="Custom title or default template title")
    notes: Optional[str] = Field(default="", description="Investigator review notes")
    include_deleted: bool = Field(default=True, description="Include recovered and deleted artifacts")
    include_unverified: bool = Field(default=True, description="Include leads under review")


class ReportSummaryItem(BaseModel):
    report_id: str
    case_id: str
    version: str
    version_number: int
    previous_version_id: Optional[str] = None
    is_current: bool
    title: str
    template_type: str
    status: str
    author: str
    created_at: float
    created_at_iso: str
    sha256: str
    summary: str
    artifact_count: int = 0
    entity_count: int = 0
    relationship_count: int = 0


class ReportDetail(BaseModel):
    report_id: str
    case_id: str
    version: str
    version_number: int
    previous_version_id: Optional[str] = None
    is_current: bool
    title: str
    template_type: str
    status: str
    author: str
    created_at: float
    created_at_iso: str
    sha256: str
    summary: str
    content_html: str
    content_markdown: str
    stats: Dict[str, Any] = Field(default_factory=dict)
    source_scope: Dict[str, Any] = Field(default_factory=dict)
    legal_draft: Dict[str, Any] = Field(default_factory=dict)
