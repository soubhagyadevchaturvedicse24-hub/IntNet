"""
API Endpoints for Authentication, Role-Based Access Control, and Policy-Driven Authorization (Slice 1).
Exposes protected case, evidence, report, judicial, and audit endpoints with BOLA and BFLA security controls.
"""

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from typing import Optional, List, Dict, Any

from src.auth.models import LoginRequest, TokenResponse, UserPublic, TokenPayload
from src.auth.service import AuthService
from src.authorization.policy_engine import PolicyEngine, AuthorizationRequest
from src.audit.service import AuditService

router = APIRouter(prefix="/api/v1", tags=["Security & Auth"])

# Module Singletons for Slice 1
auth_service = AuthService()
policy_engine = PolicyEngine()
audit_service = AuditService()


def get_current_user(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
) -> TokenPayload:
    raw_token = None
    if authorization:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization Header scheme. Must be Bearer token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        raw_token = parts[1]
    elif token:
        raw_token = token

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Header or token query param. Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = auth_service.verify_access_token(raw_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def verify_authorization(
    action: str,
    resource_type: str,
    resource_id: str,
    target_case_id: str,
    actor: TokenPayload,
    resource_owner_case_id: Optional[str] = None
):
    # Fetch actor's full user record to retrieve authorized case scope
    user = auth_service.get_user_by_id(actor.sub)
    user_authorized_cases = user.authorized_case_ids if user else []

    req = AuthorizationRequest(
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        target_case_id=target_case_id,
        resource_owner_case_id=resource_owner_case_id
    )

    decision = policy_engine.evaluate(req, user_authorized_cases)

    # Record Audit Log for every security check
    audit_service.record_event(
        actor_id=actor.sub,
        actor_role=actor.role.value,
        case_id=target_case_id,
        action=action,
        target_resource=f"{resource_type}:{resource_id}",
        decision="ALLOW" if decision.allowed else "DENY",
        metadata={"reason": decision.reason}
    )

    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization Denied: {decision.reason}"
        )


@router.post("/auth/login", response_model=TokenResponse)
def login(credentials: LoginRequest):
    user = auth_service.authenticate_user(credentials.username, credentials.password)
    if not user:
        # Audit failed login attempt
        audit_service.record_event(
            actor_id=credentials.username,
            actor_role="UNKNOWN",
            case_id="GLOBAL",
            action="LOGIN",
            target_resource="auth:login",
            decision="DENY",
            metadata={"reason": "Invalid username or password"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    token = auth_service.create_access_token(user)
    
    audit_service.record_event(
        actor_id=user.user_id,
        actor_role=user.role.value,
        case_id="GLOBAL",
        action="LOGIN",
        target_resource="auth:login",
        decision="ALLOW"
    )

    return TokenResponse(
        access_token=token,
        expires_in=3600,
        user=UserPublic(
            user_id=user.user_id,
            username=user.username,
            role=user.role,
            judicial_context=user.judicial_context,
            authorized_case_ids=user.authorized_case_ids,
            is_active=user.is_active
        )
    )


@router.get("/auth/me", response_model=UserPublic)
def get_me(current_user: TokenPayload = Depends(get_current_user)):
    user = auth_service.get_user_by_id(current_user.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserPublic(
        user_id=user.user_id,
        username=user.username,
        role=user.role,
        judicial_context=user.judicial_context,
        authorized_case_ids=user.authorized_case_ids,
        is_active=user.is_active
    )


@router.get("/cases/{case_id}")
def get_case_details(case_id: str, current_user: TokenPayload = Depends(get_current_user)):
    verify_authorization(
        action="READ_CASE",
        resource_type="case",
        resource_id=case_id,
        target_case_id=case_id,
        actor=current_user
    )
    return {
        "case_id": case_id,
        "title": f"Case File {case_id}",
        "status": "ACTIVE",
        "jurisdiction": "DELHI_DISTRICT",
        "description": "Confidential investigative case payload."
    }


@router.get("/cases/{case_id}/evidence/{evidence_id}")
def get_case_evidence(case_id: str, evidence_id: str, current_user: TokenPayload = Depends(get_current_user)):
    verify_authorization(
        action="READ_EVIDENCE",
        resource_type="evidence",
        resource_id=evidence_id,
        target_case_id=case_id,
        actor=current_user
    )
    return {
        "evidence_id": evidence_id,
        "case_id": case_id,
        "media_type": "FORENSIC_RAW_IMAGE",
        "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "status": "PRESERVED"
    }


@router.post("/cases/{case_id}/judicial_override")
def issue_judicial_override(case_id: str, current_user: TokenPayload = Depends(get_current_user)):
    verify_authorization(
        action="JUDICIAL_OVERRIDE",
        resource_type="judicial_warrant",
        resource_id=f"WARRANT-{case_id}",
        target_case_id=case_id,
        actor=current_user
    )
    return {
        "status": "WARRANT_GRANTED",
        "case_id": case_id,
        "issued_by": current_user.username,
        "judicial_court": current_user.judicial_context.court_level if current_user.judicial_context else "SUPERIOR"
    }


@router.get("/audit/logs")
def get_audit_logs(current_user: TokenPayload = Depends(get_current_user)):
    verify_authorization(
        action="VIEW_AUDIT_LOGS",
        resource_type="audit_log",
        resource_id="GLOBAL_AUDIT_TRAIL",
        target_case_id="GLOBAL",
        actor=current_user
    )
    is_valid = audit_service.verify_integrity()
    return {
        "integrity_chain_valid": is_valid,
        "total_events": len(audit_service.get_events()),
        "events": [e.model_dump() for e in audit_service.get_events()]
    }


@router.get("/judicial/judges")
@router.get("/judges")
def list_judicial_judges(current_user: TokenPayload = Depends(get_current_user)):
    """
    Returns list of active COURT_JUDGE accounts for dynamic case assignment.
    Never hardcodes judge IDs on the frontend.
    """
    judges = auth_service.get_judges()
    return [
        {
            "user_id": u.user_id,
            "username": u.username,
            "role": u.role.value,
            "court_level": u.judicial_context.court_level.value if u.judicial_context else "SPECIFIC_COURT",
            "assigned_court_id": u.judicial_context.assigned_court_id if u.judicial_context else None,
            "jurisdiction_code": u.judicial_context.jurisdiction_code if u.judicial_context else "NATIONAL",
            "display_name": f"{u.username} ({u.judicial_context.court_level.value if u.judicial_context else 'COURT'} - {u.judicial_context.jurisdiction_code or u.judicial_context.assigned_court_id or 'NATIONAL'})"
        }
        for u in judges
    ]

