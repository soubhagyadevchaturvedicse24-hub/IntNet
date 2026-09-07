"""
API Endpoints for Entity Resolution & Graph Construction (Slice 5).
Exposes REST endpoints for transforming EvidenceContract_v1 observations into evidence-backed Kùzu graph networks.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from src.auth.models import TokenPayload
from src.api.auth_routes import get_current_user, auth_service, policy_engine, audit_service
from src.api.processing_routes import processing_service
from src.entity_resolution.service import EntityGraphService
from src.entity_resolution.graph_integrator import KuzuEntityGraphIntegrator

router = APIRouter(prefix="/api/v1/cases/{case_id}/graph", tags=["Entity Resolution & Graph Construction"])

# Shared EntityGraphService singleton
graph_integrator = KuzuEntityGraphIntegrator()
entity_graph_service = EntityGraphService(
    graph_integrator=graph_integrator,
    processing_service=processing_service,
    policy_engine=policy_engine,
    audit_service=audit_service,
    auth_service=auth_service
)


class HumanVerificationRequest(BaseModel):
    target_id: str
    status_decision: str  # "UNDER_REVIEW", "HUMAN_VERIFIED_LEAD", "REJECTED_ASSOCIATION"
    notes: Optional[str] = ""


@router.post("/ingest/{job_id}", status_code=status.HTTP_201_CREATED)
def ingest_evidence_contract(
    case_id: str,
    job_id: str,
    current_user: TokenPayload = Depends(get_current_user)
):
    try:
        res = entity_graph_service.ingest_evidence_contract(
            actor=current_user,
            case_id=case_id,
            job_id=job_id
        )
        return res
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization Denied: {str(e)}"
        )
    except (ValueError, KeyError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Graph Ingestion Failed: {str(e)}"
        )


@router.get("")
def get_case_graph(
    case_id: str,
    demo: bool = False,
    current_user: TokenPayload = Depends(get_current_user)
):
    try:
        graph_data = entity_graph_service.get_case_graph(current_user, case_id, demo=demo)
        return graph_data
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization Denied: {str(e)}"
        )


@router.get("/entity/{entity_id}")
def get_entity_details(
    case_id: str,
    entity_id: str,
    demo: bool = False,
    current_user: TokenPayload = Depends(get_current_user)
):
    try:
        details = entity_graph_service.get_entity_details(
            actor=current_user,
            case_id=case_id,
            entity_id=entity_id,
            demo=demo
        )
        if not details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity '{entity_id}' not found in case '{case_id}'."
            )
        return details
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization Denied: {str(e)}"
        )


@router.get("/relationship/{edge_id}")
def get_relationship_details(
    case_id: str,
    edge_id: str,
    demo: bool = False,
    current_user: TokenPayload = Depends(get_current_user)
):
    try:
        details = entity_graph_service.get_relationship_details(
            actor=current_user,
            case_id=case_id,
            edge_id=edge_id,
            demo=demo
        )
        if not details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Relationship '{edge_id}' not found in case '{case_id}'."
            )
        return details
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization Denied: {str(e)}"
        )


@router.get("/neighbors/{entity_id}")
def get_neighbors(
    case_id: str,
    entity_id: str,
    hops: int = 1,
    demo: bool = False,
    current_user: TokenPayload = Depends(get_current_user)
):
    try:
        return entity_graph_service.get_neighbors(
            actor=current_user,
            case_id=case_id,
            entity_id=entity_id,
            hops=hops,
            demo=demo
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization Denied: {str(e)}"
        )


@router.get("/shortest_path")
def get_shortest_path(
    case_id: str,
    src_id: str,
    tgt_id: str,
    demo: bool = False,
    current_user: TokenPayload = Depends(get_current_user)
):
    try:
        return entity_graph_service.get_shortest_path(
            actor=current_user,
            case_id=case_id,
            src_id=src_id,
            tgt_id=tgt_id,
            demo=demo
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization Denied: {str(e)}"
        )


@router.post("/verify")
def verify_human_lead(
    case_id: str,
    req: HumanVerificationRequest,
    current_user: TokenPayload = Depends(get_current_user)
):
    try:
        res = entity_graph_service.verify_human_lead(
            actor=current_user,
            case_id=case_id,
            target_id=req.target_id,
            status_decision=req.status_decision,
            notes=req.notes
        )
        return res
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization Denied: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
