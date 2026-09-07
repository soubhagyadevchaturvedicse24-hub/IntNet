"""
Identity and User Domain Models for CRIMENET.
Defines user roles, judicial context, and security credentials.
"""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    INVESTIGATION_OFFICER = "INVESTIGATION_OFFICER"
    HIGHER_AUTHORITY = "HIGHER_AUTHORITY"
    COURT_JUDGE = "COURT_JUDGE"


class CourtLevel(str, Enum):
    SPECIFIC_COURT = "SPECIFIC_COURT"
    HIGH_COURT = "HIGH_COURT"
    SUPREME_COURT = "SUPREME_COURT"


class JudicialContext(BaseModel):
    court_level: CourtLevel
    assigned_court_id: Optional[str] = None  # e.g., "COURT-DL-001"
    jurisdiction_code: Optional[str] = None  # e.g., "DELHI_STATE", "NATIONAL"


class User(BaseModel):
    user_id: str
    username: str
    password_hash: str
    role: UserRole
    judicial_context: Optional[JudicialContext] = None
    authorized_case_ids: List[str] = Field(default_factory=list)
    is_active: bool = True


class UserPublic(BaseModel):
    user_id: str
    username: str
    role: UserRole
    judicial_context: Optional[JudicialContext] = None
    authorized_case_ids: List[str] = Field(default_factory=list)
    is_active: bool


class TokenPayload(BaseModel):
    sub: str  # user_id
    username: str
    role: UserRole
    judicial_context: Optional[JudicialContext] = None
    exp: int
    jti: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic
