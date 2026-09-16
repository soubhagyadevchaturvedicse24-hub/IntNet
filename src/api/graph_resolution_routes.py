"""
API Endpoints for Entity Resolution & Graph Construction (Slice 5 & Slice 8B).
Exposes REST endpoints for transforming EvidenceContract_v1 and deep parsed observations
into evidence-backed Kùzu graph networks with full case isolation.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from src.auth.models import TokenPayload
from src.api.auth_routes import get_current_user, auth_service, policy_engine, audit_service
from src.api.processing_routes import processing_service
from src.parsers.repository import SQLiteParsedArtifactRepository
from src.entity_resolution.service import EntityGraphService
from src.entity_resolution.graph_integrator import KuzuEntityGraphIntegrator
from src.entity_resolution.signal_extractor import ObservationSignalExtractor

router = APIRouter(prefix="/api/v1/cases/{case_id}/graph", tags=["Entity Resolution & Graph Construction"])

# Shared EntityGraphService singleton
graph_integrator = KuzuEntityGraphIntegrator()
parsed_artifact_repo = SQLiteParsedArtifactRepository()
signal_extractor = ObservationSignalExtractor()

entity_graph_service = EntityGraphService(
    graph_integrator=graph_integrator,
    processing_service=processing_service,
    policy_engine=policy_engine,
    audit_service=audit_service,
    auth_service=auth_service,
    parsed_repo=parsed_artifact_repo,
    signal_extractor=signal_extractor,
)
processing_service.entity_graph_service = entity_graph_service


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


@router.post("/ingest-observations", status_code=status.HTTP_201_CREATED)
def ingest_parsed_observations(
    case_id: str,
    artifact_id: Optional[str] = Query(None, description="Scope ingestion to a specific parsed artifact ID"),
    job_id: Optional[str] = Query(None, description="Scope ingestion to a specific processing job ID"),
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Slice 8B REST Ingestion Bridge:
    Transforms deep parsed observations into normalized signals, canonical entities,
    and evidence-backed relationships in the case knowledge graph.
    """
    try:
        res = entity_graph_service.ingest_parsed_observations(
            actor=current_user,
            case_id=case_id,
            artifact_id=artifact_id,
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
            detail=f"Observation Ingestion Failed: {str(e)}"
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


@router.get("/analytics")
def get_graph_analytics(
    case_id: str,
    source_id: Optional[str] = Query(None, description="Optional source entity ID for shortest path calculation"),
    target_id: Optional[str] = Query(None, description="Optional target entity ID for shortest path calculation"),
    entity_id: Optional[str] = Query(None, description="Optional entity ID for 1-hop / 2-hop neighbor inspection"),
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Slice 8D Forensic Graph Analytics:
    Computes deterministic graph analytics on case-scoped knowledge graphs:
    1. Degree (unique communicating neighbors: in, out, total)
    2. Weighted communication frequency (observed communication counts)
    3. Betweenness centrality (inverse frequency distance)
    4. PageRank (weighted communication flow)
    5. Weakly & strongly connected components
    6. Louvain community detection (undirected weighted projection)
    7. Weighted shortest path (inverse frequency distance)
    8. 1-hop / 2-hop neighbors
    9. Descriptive timestamp patterns (histograms and time windows)
    """
    try:
        return entity_graph_service.compute_graph_analytics(
            actor=current_user,
            case_id=case_id,
            source_id=source_id,
            target_id=target_id,
            entity_id=entity_id
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization Denied: {str(e)}"
        )

