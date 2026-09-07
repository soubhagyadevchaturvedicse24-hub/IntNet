"""
API Endpoints for Case Management Domain (Slice 2).
Exposes protected REST endpoints for creating, retrieving, updating, and reopening cases.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List

from src.auth.models import TokenPayload
from src.api.auth_routes import get_current_user, auth_service, policy_engine, audit_service
from src.cases.models import Case, CaseCreate, CaseUpdate, CaseResponse
from src.cases.service import CaseService
from src.cases.repository import SQLiteCaseRepository

router = APIRouter(prefix="/api/v1/cases", tags=["Case Management"])

# Instantiate singleton CaseService sharing the auth, policy, and audit instances
case_repository = SQLiteCaseRepository()
case_service = CaseService(
    repository=case_repository,
    policy_engine=policy_engine,
    audit_service=audit_service,
    auth_service=auth_service
)


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(req: CaseCreate, current_user: TokenPayload = Depends(get_current_user)):
    try:
        case = case_service.create_case(current_user, req)
        return CaseResponse(**case.model_dump())
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization Denied: {str(e)}"
        )


@router.get("", response_model=List[CaseResponse])
def list_cases(current_user: TokenPayload = Depends(get_current_user)):
    cases = case_service.list_cases(current_user)
    return [CaseResponse(**c.model_dump()) for c in cases]


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(case_id: str, current_user: TokenPayload = Depends(get_current_user)):
    try:
        case = case_service.get_case(current_user, case_id)
        if not case:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
        return CaseResponse(**case.model_dump())
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization Denied: {str(e)}"
        )


@router.put("/{case_id}", response_model=CaseResponse)
def update_case(case_id: str, req: CaseUpdate, current_user: TokenPayload = Depends(get_current_user)):
    try:
        case = case_service.update_case(current_user, case_id, req)
        if not case:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
        return CaseResponse(**case.model_dump())
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization Denied: {str(e)}"
        )


@router.post("/{case_id}/reopen", response_model=CaseResponse)
def reopen_case(case_id: str, current_user: TokenPayload = Depends(get_current_user)):
    try:
        case = case_service.reopen_case(current_user, case_id)
        if not case:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
        return CaseResponse(**case.model_dump())
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization Denied: {str(e)}"
        )


@router.delete("/{case_id}", status_code=status.HTTP_200_OK)
def delete_case(case_id: str, current_user: TokenPayload = Depends(get_current_user)):
    try:
        deleted = case_service.delete_case(current_user, case_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
        return {"status": "DELETED", "case_id": case_id}
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization Denied: {str(e)}"
        )
