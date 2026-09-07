"""
Deep Artifact Parsing API Router for CRIMENET (Slice 8A).
Exposes case-scoped deep inspection and observation retrieval endpoints
with server-side PolicyEngine BOLA authorization and audit trail tracking.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.auth.models import TokenPayload
from src.api.auth_routes import get_current_user
from src.parsers.models import ParsedArtifact
from src.parsers.service import DeepParsingService

router = APIRouter(prefix="/api/v1/cases/{case_id}/artifacts/{artifact_id}", tags=["Deep Artifact Parsing"])

parsing_service = DeepParsingService()


@router.post("/parse", response_model=ParsedArtifact)
def trigger_artifact_parse(
    case_id: str,
    artifact_id: str,
    force: bool = Query(False, description="Force re-parsing even if cached result exists"),
    actor: TokenPayload = Depends(get_current_user),
):
    """
    Executes deep forensic inspection on an artifact (PDF, Image, SQLite).
    Enforces server-side BOLA authorization and resolves file strictly through
    internal server storage boundaries.
    """
    try:
        parsed = parsing_service.parse_artifact(
            actor=actor,
            case_id=case_id,
            artifact_id=artifact_id,
            force_reparse=force,
        )
        return parsed
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except KeyError as ke:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ke))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.get("/parsed", response_model=ParsedArtifact)
def get_artifact_parsed_observations(
    case_id: str,
    artifact_id: str,
    actor: TokenPayload = Depends(get_current_user),
):
    """
    Retrieves existing deep parsed observations and metadata for an artifact.
    Returns 404 if the artifact has not yet undergone deep parsing.
    """
    try:
        parsed = parsing_service.get_parsed_artifact(
            actor=actor,
            case_id=case_id,
            artifact_id=artifact_id,
        )
        if not parsed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' has not been parsed yet.",
            )
        return parsed
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except KeyError as ke:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ke))
