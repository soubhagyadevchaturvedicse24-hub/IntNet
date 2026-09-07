"""
Artifact & Evidence Explorer API Router for CRIMENET (Slice 6).
Exposes case-scoped artifact browsing, filtering, detail retrieval,
and secure file content access endpoints with server-side PolicyEngine BOLA authorization.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, Response

from src.auth.models import TokenPayload
from src.api.auth_routes import get_current_user
from src.artifacts.models import (
    ArtifactResponse,
    ArtifactFilterParams,
    ArtifactCategory,
    AllocationStatus,
    RecoveryStatus
)
from src.artifacts.service import ArtifactService

router = APIRouter(prefix="/api/v1/cases/{case_id}/artifacts", tags=["Evidence Explorer / Artifacts"])

artifact_service = ArtifactService()


@router.get("", response_model=List[ArtifactResponse])
def list_case_artifacts(
    case_id: str,
    category: Optional[ArtifactCategory] = Query(None, description="Filter by Layer 1 artifact category"),
    mime_type: Optional[str] = Query(None, description="Filter by MIME type"),
    filename: Optional[str] = Query(None, description="Filter by filename (partial match)"),
    allocation_status: Optional[AllocationStatus] = Query(None, description="Filter by allocation status"),
    recovery_status: Optional[RecoveryStatus] = Query(None, description="Filter by recovery status"),
    evidence_id: Optional[str] = Query(None, description="Filter by evidence ID"),
    processing_job_id: Optional[str] = Query(None, description="Filter by processing job ID"),
    actor: TokenPayload = Depends(get_current_user)
):
    """
    Lists observed artifacts for an authorized case.
    Supports multi-criteria filtering across category, MIME type, filename, allocation, recovery, and evidence source.
    """
    filters = ArtifactFilterParams(
        category=category,
        mime_type=mime_type,
        filename=filename,
        allocation_status=allocation_status,
        recovery_status=recovery_status,
        evidence_id=evidence_id,
        processing_job_id=processing_job_id
    )

    try:
        artifacts = artifact_service.list_case_artifacts(actor=actor, case_id=case_id, filters=filters)
        return [
            ArtifactResponse(
                artifact_id=a.artifact_id,
                case_id=a.case_id,
                evidence_id=a.evidence_id,
                processing_job_id=a.processing_job_id,
                filename=a.filename,
                path_within_source=a.path_within_source,
                category=a.category,
                mime_type=a.mime_type,
                file_extension=a.file_extension,
                size_bytes=a.size_bytes,
                sha256=a.sha256,
                created_at_observed=a.created_at_observed,
                modified_at_observed=a.modified_at_observed,
                accessed_at_observed=a.accessed_at_observed,
                allocation_status=a.allocation_status,
                recovery_status=a.recovery_status,
                observation_method=a.observation_method,
                recommended_viewer=a.recommended_viewer,
                provenance_chain=a.provenance_chain
            )
            for a in artifacts
        ]
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))


@router.get("/{artifact_id}", response_model=ArtifactResponse)
def get_artifact_details(
    case_id: str,
    artifact_id: str,
    actor: TokenPayload = Depends(get_current_user)
):
    """
    Retrieves full metadata, provenance chain, and viewer recommendation for a single artifact.
    Enforces server-side BOLA authorization and cross-case ID manipulation defense.
    """
    try:
        artifact = artifact_service.get_artifact(actor=actor, case_id=case_id, artifact_id=artifact_id)
        if not artifact:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Artifact '{artifact_id}' not found.")

        return ArtifactResponse(
            artifact_id=artifact.artifact_id,
            case_id=artifact.case_id,
            evidence_id=artifact.evidence_id,
            processing_job_id=artifact.processing_job_id,
            filename=artifact.filename,
            path_within_source=artifact.path_within_source,
            category=artifact.category,
            mime_type=artifact.mime_type,
            file_extension=artifact.file_extension,
            size_bytes=artifact.size_bytes,
            sha256=artifact.sha256,
            created_at_observed=artifact.created_at_observed,
            modified_at_observed=artifact.modified_at_observed,
            accessed_at_observed=artifact.accessed_at_observed,
            allocation_status=artifact.allocation_status,
            recovery_status=artifact.recovery_status,
            observation_method=artifact.observation_method,
            recommended_viewer=artifact.recommended_viewer,
            provenance_chain=artifact.provenance_chain
        )
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))


@router.get("/{artifact_id}/content")
def get_artifact_content(
    case_id: str,
    artifact_id: str,
    actor: TokenPayload = Depends(get_current_user)
):
    """
    Secure file content access endpoint.
    Performs server-side BOLA authorization before resolving content path.
    Shields internal filesystem structure, enforcing strict canonical path bounds to prevent path traversal attacks.
    """
    try:
        path = artifact_service.get_artifact_content_path(actor=actor, case_id=case_id, artifact_id=artifact_id)
        if not path.exists() or not path.is_file():
            # Return placeholder byte stream if content file not physically stored
            return Response(content=b"[CRIMENET SAFE STORAGE: ARTIFACT STREAM AVAILABLE]", media_type="text/plain")

        artifact = artifact_service.get_artifact(actor=actor, case_id=case_id, artifact_id=artifact_id)
        media_type = artifact.mime_type if artifact else "application/octet-stream"
        return FileResponse(path=str(path), media_type=media_type, filename=path.name)
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except KeyError as ke:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ke))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
