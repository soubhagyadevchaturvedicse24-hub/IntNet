"""
FastAPI Backend Application — CRIMENET Investigator Graph Intelligence & CCC UI API
Serves investigator graph endpoints, CCC relationship scoring, evidence traceability lookup,
and embedded Cytoscape.js visualizer interface.
"""

import os
import sys
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.api.graph_service import GraphIntelligenceService, shared_demo_graph_service as graph_service
from src.api.auth_routes import router as auth_router
from src.api.case_routes import router as case_router
from src.api.evidence_routes import router as evidence_router, evidence_discovery_router
from src.api.processing_routes import router as processing_router
from src.api.graph_resolution_routes import router as graph_res_router
from src.api.artifact_routes import router as artifact_router
from src.api.parsing_routes import router as parsing_router
from src.api.report_routes import router as report_router, global_reports_router
from src.api.location_routes import router as location_router

app = FastAPI(
    title="CRIMENET Investigator Graph Intelligence API",
    version="1.0.0",
    description="AI-Assisted Decision Support API for Evidence-Backed Graph Exploration & CCC Scoring"
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(case_router)
app.include_router(evidence_router)
app.include_router(evidence_discovery_router)
app.include_router(auth_router)
app.include_router(processing_router)
app.include_router(graph_res_router)
app.include_router(artifact_router)
app.include_router(parsing_router)
app.include_router(report_router)
app.include_router(global_reports_router)
app.include_router(location_router)

# Serve brand/static assets (banners, illustrations, buttons)
_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(_STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


class VerificationRequest(BaseModel):
    entity_id: str
    status: str  # "UNDER_REVIEW", "HUMAN_VERIFIED_LEAD", "REJECTED_ASSOCIATION"
    notes: Optional[str] = ""

@app.get("/api/graph/overview")
def get_graph_overview():
    """Returns overall graph structure (nodes & edges) with evidence references and CCC scores."""
    return graph_service.get_graph_overview()

@app.get("/api/entity/{entity_id}")
def get_entity_details(entity_id: str):
    """Returns canonical entity metadata, observed values, and provenance."""
    details = graph_service.get_entity_details(entity_id)
    if not details:
        raise HTTPException(status_code=404, detail="Entity ID not found")
    return details

@app.get("/api/relationship/{edge_id}")
def get_relationship_details(edge_id: str):
    """Returns relationship details, CCC score breakdown, and originating evidence contract references."""
    details = graph_service.get_relationship_details(edge_id)
    if not details:
        raise HTTPException(status_code=404, detail="Relationship ID not found")
    return details

@app.get("/api/evidence/{evidence_id}")
def get_evidence_traceability(evidence_id: str):
    """Answers 'Why does this relationship exist?' with evidence chain-of-custody."""
    details = graph_service.get_evidence_traceability(evidence_id)
    if not details:
        raise HTTPException(status_code=404, detail="Evidence ID not found")
    return details

@app.get("/api/graph/neighbors/{entity_id}")
def get_neighbors(entity_id: str, hops: int = Query(default=1, ge=1, le=2)):
    """Returns 1-hop or 2-hop neighborhood of a given entity."""
    return graph_service.get_neighbors(entity_id, hops=hops)

@app.get("/api/graph/shortest_path")
def get_shortest_path(src_id: str, tgt_id: str):
    """Calculates shortest path between two suspect entities."""
    return graph_service.get_shortest_path(src_id, tgt_id)

@app.post("/api/verification/verify")
def verify_entity(req: VerificationRequest):
    """Logs human verification decision (UNDER_REVIEW, HUMAN_VERIFIED_LEAD, REJECTED_ASSOCIATION)."""
    return graph_service.verify_entity(req.entity_id, req.status, req.notes)

WORKSPACE_HTML_PATH = os.path.join(os.path.dirname(__file__), "workspace.html")

@app.get("/", response_class=HTMLResponse)
@app.get("/workspace", response_class=HTMLResponse)
@app.get("/workspace.html", response_class=HTMLResponse)
def get_investigator_ui():
    """Serves the CRIMENET Investigator Workspace single-page interface with no-cache headers."""
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }
    if os.path.exists(WORKSPACE_HTML_PATH):
        with open(WORKSPACE_HTML_PATH, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), headers=headers)
    return HTMLResponse(content="<html><body><h3>CRIMENET Workspace file not found</h3></body></html>", status_code=404, headers=headers)

