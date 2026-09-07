"""
API Endpoints for Forensic Image Processing & Observation Engine (Slice 4).
Exposes REST endpoints for launching asynchronous processing jobs, checking job status, and retrieving EvidenceContract_v1 payloads.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List, Dict, Any

from src.auth.models import TokenPayload
from src.api.auth_routes import get_current_user, auth_service, policy_engine, audit_service
from src.api.evidence_routes import evidence_service
from src.processing.models import ProcessingJobResponse, ProcessingJobCreate
from src.processing.service import ProcessingService
from src.processing.repository import SQLiteProcessingRepository
from src.processing.engine import RawDiskObservationEngine

router = APIRouter(prefix="/api/v1", tags=["Forensic Processing & Observation Engine"])

# Shared ProcessingService singleton
processing_repository = SQLiteProcessingRepository()
observation_engine = RawDiskObservationEngine()
processing_service = ProcessingService(
    repository=processing_repository,
    engine=observation_engine,
    evidence_service=evidence_service,
    policy_engine=policy_engine,
    audit_service=audit_service,
    auth_service=auth_service
)


@router.post("/cases/{case_id}/evidence/{evidence_id}/process", response_model=ProcessingJobResponse, status_code=status.HTTP_202_ACCEPTED)
def request_processing_job(
    case_id: str,
    evidence_id: str,
    create_req: Optional[ProcessingJobCreate] = None,
    current_user: TokenPayload = Depends(get_current_user)
):
    try:
        job = processing_service.create_processing_job(
            actor=current_user,
            case_id=case_id,
            evidence_id=evidence_id,
            create_req=create_req
        )
        return ProcessingJobResponse(**job.model_dump())
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization Denied: {str(e)}"
        )
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Processing Job Creation Failed: {str(e)}"
        )


@router.get("/cases/{case_id}/evidence/{evidence_id}/jobs", response_model=List[ProcessingJobResponse])
def list_evidence_jobs(case_id: str, evidence_id: str, current_user: TokenPayload = Depends(get_current_user)):
    try:
        jobs = processing_service.list_evidence_jobs(current_user, case_id, evidence_id)
        return [ProcessingJobResponse(**j.model_dump()) for j in jobs]
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization Denied: {str(e)}"
        )


@router.get("/processing/jobs/{job_id}", response_model=ProcessingJobResponse)
def get_job_status(job_id: str, current_user: TokenPayload = Depends(get_current_user)):
    try:
        job = processing_service.get_job(current_user, job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing job not found")
        return ProcessingJobResponse(**job.model_dump())
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization Denied: {str(e)}"
        )


@router.get("/processing/jobs/{job_id}/contract")
def get_evidence_contract(job_id: str, current_user: TokenPayload = Depends(get_current_user)):
    try:
        contract = processing_service.get_evidence_contract(current_user, job_id)
        if not contract:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence contract not found or job not completed")
        return contract
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization Denied: {str(e)}"
        )
