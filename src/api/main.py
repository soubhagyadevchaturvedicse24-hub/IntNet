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
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.api.graph_service import GraphIntelligenceService

app = FastAPI(
    title="CRIMENET Investigator Graph Intelligence API",
    version="1.0.0",
    description="AI-Assisted Decision Support API for Evidence-Backed Graph Exploration & CCC Scoring"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

graph_service = GraphIntelligenceService()

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

@app.get("/", response_class=HTMLResponse)
def get_investigator_ui():
    """Serves the polished single-page Investigator Intelligence Lab graph dashboard (Screenshot A target + Interactive Cytoscape)."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CRIMENET // Investigator Intelligence Lab</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.26.0/cytoscape.min.js"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #050a16;
            --panel-bg: #070e1f;
            --panel-elevated: #0d172e;
            --panel-border: rgba(56, 189, 248, 0.16);
            --accent-cyan: #00f0ff;
            --accent-cyan-glow: rgba(0, 240, 255, 0.35);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            
            --layer-red: #ef4444;
            --layer-red-glow: rgba(239, 68, 68, 0.45);
            --layer-yellow: #f59e0b;
            --layer-yellow-glow: rgba(245, 158, 11, 0.4);
            --layer-green: #10b981;
            --layer-green-glow: rgba(16, 185, 129, 0.4);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', system-ui, -apple-system, sans-serif; }
        body { background: var(--bg-dark); color: var(--text-primary); height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

        /* HEADER */
        header {
            background: #040814;
            height: 52px;
            padding: 0 20px;
            border-bottom: 1px solid var(--panel-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 100;
        }

        .brand-container { display: flex; align-items: center; gap: 12px; }
        .brand-logo {
            width: 30px; height: 30px;
            background: radial-gradient(circle, rgba(0,240,255,0.25) 0%, transparent 70%);
            border: 1.5px solid var(--accent-cyan);
            border-radius: 8px;
            display: flex; align-items: center; justify-content: center;
            color: var(--accent-cyan);
            box-shadow: 0 0 12px var(--accent-cyan-glow);
        }
        .brand-title { font-weight: 700; font-size: 14px; letter-spacing: 0.8px; color: #ffffff; display: flex; align-items: center; gap: 8px; }
        .brand-title span { color: var(--accent-cyan); font-weight: 400; }
        .brand-sub { font-size: 9px; letter-spacing: 2px; color: var(--accent-cyan); text-transform: uppercase; font-weight: 600; margin-top: 1px; }

        .header-right { display: flex; align-items: center; gap: 16px; }
        
        .search-box {
            position: relative;
            width: 290px;
        }
        .search-box input {
            width: 100%;
            background: rgba(13, 23, 46, 0.85);
            border: 1px solid var(--panel-border);
            border-radius: 6px;
            padding: 7px 12px 7px 32px;
            color: #fff;
            font-size: 12px;
            outline: none;
            transition: all 0.2s ease;
        }
        .search-box input:focus { border-color: var(--accent-cyan); box-shadow: 0 0 10px var(--accent-cyan-glow); }
        .search-icon { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); width: 14px; height: 14px; color: var(--text-muted); }

        .header-btn {
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid var(--panel-border);
            color: var(--text-secondary);
            height: 32px;
            padding: 0 12px;
            border-radius: 6px;
            display: flex; align-items: center; justify-content: center; gap: 6px;
            cursor: pointer;
            font-size: 11px; font-weight: 600;
            transition: all 0.2s;
        }
        .header-btn:hover { color: #fff; border-color: var(--accent-cyan); box-shadow: 0 0 10px var(--accent-cyan-glow); }

        /* MAIN CONTAINER */
        .workspace { display: flex; flex: 1; height: calc(100vh - 80px); overflow: hidden; }

        /* LEFT PANEL */
        .panel-left {
            width: 300px;
            background: var(--panel-bg);
            border-right: 1px solid var(--panel-border);
            display: flex;
            flex-direction: column;
            padding: 14px;
            gap: 12px;
            overflow-y: auto;
            z-index: 10;
        }

        .panel-sec-title {
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.2px;
            color: #94a3b8;
            text-transform: uppercase;
            margin-bottom: 6px;
            display: flex; align-items: center; justify-content: space-between;
            cursor: pointer;
            user-select: none;
            transition: color 0.15s;
        }
        .panel-sec-title:hover { color: var(--accent-cyan); }
        .chevron-icon { transition: transform 0.2s ease; color: var(--accent-cyan); }
        .sec-content { display: flex; flex-direction: column; gap: 8px; }

        .card-stat {
            background: var(--panel-elevated);
            border: 1px solid var(--panel-border);
            border-radius: 8px;
            padding: 10px 12px;
            display: flex; flex-direction: column; gap: 8px;
        }
        .stat-row { display: flex; justify-content: space-between; align-items: center; font-size: 12px; }
        .stat-label { display: flex; align-items: center; gap: 8px; color: var(--text-secondary); }
        .stat-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
        .stat-value { font-weight: 700; font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #fff; }

        .profile-card {
            background: var(--panel-elevated);
            border: 1px solid var(--panel-border);
            border-radius: 8px;
            padding: 12px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .profile-avatar {
            width: 44px; height: 44px;
            border-radius: 50%;
            background: radial-gradient(circle, #ef444433 0%, #0f172a 100%);
            border: 2px solid var(--layer-red);
            box-shadow: 0 0 14px var(--layer-red-glow);
            display: flex; align-items: center; justify-content: center;
            color: var(--layer-red);
            flex-shrink: 0;
        }
        .profile-info h4 { font-size: 14px; font-weight: 600; color: #fff; }
        .profile-info p { font-size: 11px; color: var(--text-secondary); margin-top: 2px; }
        .pill-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 600;
            margin-top: 4px;
        }
        .pill-red { background: rgba(239, 68, 68, 0.15); color: #fca5a5; border: 1px solid var(--layer-red); }
        .pill-white { background: rgba(255, 255, 255, 0.15); color: #ffffff; border: 1px solid #ffffff; }

        .control-group { display: flex; flex-direction: column; gap: 6px; }
        .input-dark {
            background: #0a1122;
            border: 1px solid var(--panel-border);
            color: #fff;
            padding: 7px 10px;
            border-radius: 6px;
            font-size: 11px;
            outline: none;
            width: 100%;
        }
        .input-dark:focus { border-color: var(--accent-cyan); }
        .btn-ctrl {
            background: rgba(0, 240, 255, 0.08);
            border: 1px solid rgba(0, 240, 255, 0.35);
            color: var(--accent-cyan);
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 11px; font-weight: 600;
            cursor: pointer;
            display: flex; align-items: center; justify-content: center; gap: 6px;
            transition: all 0.2s;
        }
        .btn-ctrl:hover { background: var(--accent-cyan); color: #020617; box-shadow: 0 0 10px var(--accent-cyan-glow); }

        .legend-list { display: flex; flex-direction: column; gap: 8px; font-size: 11px; }
        .legend-item { display: flex; align-items: center; gap: 10px; color: var(--text-secondary); }
        .legend-line { width: 24px; height: 2px; border-radius: 1px; }

        .source-list { display: flex; flex-direction: column; gap: 8px; font-size: 11px; color: var(--text-secondary); }
        .source-item { display: flex; align-items: center; gap: 10px; }

        .panel-footer { margin-top: auto; font-size: 10px; color: var(--text-muted); display: flex; justify-content: space-between; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 10px; }

        /* CENTER GRAPH WORKSPACE */
        .panel-center {
            flex: 1;
            position: relative;
            background: #050a16;
            background-image: 
                radial-gradient(rgba(0, 240, 255, 0.04) 1px, transparent 1px),
                linear-gradient(to right, rgba(0, 240, 255, 0.015) 1px, transparent 1px),
                linear-gradient(to bottom, rgba(0, 240, 255, 0.015) 1px, transparent 1px);
            background-size: 36px 36px;
            display: flex; flex-direction: column;
            overflow: hidden;
        }

        #cy-wrapper {
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            width: 100%; height: 100%;
        }

        #glow-overlay {
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            pointer-events: none;
            z-index: 1;
        }

        #cy {
            width: 100%; height: 100%;
            position: absolute;
            top: 0; left: 0;
            z-index: 2;
        }

        /* FLOATING BOTTOM-RIGHT DOCK (LEGEND + MINIMAP) */
        .workspace-bottom-right-dock {
            position: absolute;
            bottom: 16px;
            right: 16px;
            display: flex;
            gap: 12px;
            z-index: 10;
            align-items: flex-end;
            pointer-events: auto;
        }

        .dock-card {
            background: rgba(7, 14, 31, 0.9);
            backdrop-filter: blur(14px);
            border: 1px solid var(--panel-border);
            border-radius: 8px;
            padding: 10px 14px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.6);
        }
        .dock-card h4 {
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1px;
            color: var(--accent-cyan);
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .analytical-legend { width: 250px; }
        .layer-row { display: flex; align-items: center; gap: 8px; font-size: 11px; margin-bottom: 6px; color: var(--text-primary); }
        .ring-indicator { width: 10px; height: 10px; border-radius: 50%; border: 2px solid; flex-shrink: 0; }
        .disclaimer-sub { font-size: 9.5px; color: var(--text-muted); line-height: 1.3; margin-top: 6px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 6px; }

        .minimap-container {
            width: 175px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .minimap-svg { width: 100%; height: 85px; pointer-events: none; }
        .compass-overlay { position: absolute; top: 0px; right: 0px; font-size: 8px; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; text-align: center; }
        .zoom-controls { position: absolute; bottom: 0px; right: 0px; display: flex; flex-direction: column; gap: 3px; }
        .zoom-btn { width: 20px; height: 20px; background: #0e172a; border: 1px solid var(--panel-border); color: #fff; border-radius: 4px; font-size: 11px; cursor: pointer; display: flex; align-items: center; justify-content: center; font-weight: bold; }
        .zoom-btn:hover { background: var(--accent-cyan); color: #000; }

        /* RIGHT INSPECTOR PANEL */
        .panel-right {
            width: 350px;
            background: var(--panel-bg);
            border-left: 1px solid var(--panel-border);
            display: flex;
            flex-direction: column;
            padding: 14px;
            gap: 12px;
            overflow-y: auto;
            z-index: 10;
        }

        .rai-alert {
            background: rgba(245, 158, 11, 0.08);
            border: 1px solid rgba(245, 158, 11, 0.3);
            border-radius: 8px;
            padding: 10px 12px;
            display: flex;
            gap: 10px;
        }
        .rai-alert-icon { color: var(--layer-yellow); flex-shrink: 0; margin-top: 2px; }
        .rai-alert-text h5 { font-size: 11px; font-weight: 600; color: #fde68a; margin-bottom: 2px; }
        .rai-alert-text p { font-size: 10px; color: #cbd5e1; line-height: 1.35; }

        .layer-filter-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 6px;
        }
        .btn-filter {
            background: rgba(13, 23, 46, 0.85);
            border: 1px solid var(--panel-border);
            color: var(--text-secondary);
            padding: 8px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            transition: all 0.2s;
        }
        .btn-filter:hover {
            border-color: var(--accent-cyan);
            color: #fff;
            box-shadow: 0 0 8px var(--accent-cyan-glow);
        }
        .btn-filter.active {
            background: rgba(0, 240, 255, 0.16);
            border-color: var(--accent-cyan);
            color: #fff;
            box-shadow: 0 0 10px var(--accent-cyan-glow);
        }

        .inspector-card {
            background: var(--panel-elevated);
            border: 1px solid var(--panel-border);
            border-radius: 8px;
            padding: 14px;
            display: flex; flex-direction: column; gap: 10px;
        }

        .inspector-header { display: flex; align-items: center; gap: 10px; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 10px; }
        .inspector-avatar { width: 36px; height: 36px; border-radius: 50%; background: #0f1933; border: 1.5px solid var(--accent-cyan); display: flex; align-items: center; justify-content: center; color: var(--accent-cyan); }
        
        .prop-grid { display: flex; flex-direction: column; gap: 6px; font-size: 11px; }
        .prop-item { display: flex; justify-content: space-between; align-items: center; }
        .prop-key { color: var(--text-secondary); }
        .prop-val { font-weight: 600; color: var(--text-primary); font-family: 'JetBrains Mono', monospace; font-size: 11px; }
        
        .provenance-box {
            background: #081226;
            border: 1px solid rgba(0, 240, 255, 0.18);
            border-radius: 6px;
            padding: 10px;
            margin-top: 4px;
        }
        .provenance-box h5 { font-size: 10px; text-transform: uppercase; color: var(--accent-cyan); letter-spacing: 0.8px; margin-bottom: 6px; }
        .provenance-box p { font-size: 11px; color: var(--text-secondary); line-height: 1.4; margin-bottom: 4px; }

        .btn-action-group { display: flex; gap: 6px; margin-top: 8px; }
        .btn-act {
            flex: 1;
            padding: 8px 6px;
            border-radius: 6px;
            font-size: 10px;
            font-weight: 700;
            border: none;
            cursor: pointer;
            display: flex; align-items: center; justify-content: center; gap: 4px;
            transition: all 0.2s;
            text-transform: uppercase;
        }
        .btn-review-lead { background: #f59e0b; color: #000; }
        .btn-review-lead:hover { background: #fde047; }
        .btn-verify-lead { background: #10b981; color: #000; }
        .btn-verify-lead:hover { background: #34d399; }
        .btn-reject-lead { background: #ef4444; color: #fff; }
        .btn-reject-lead:hover { background: #f87171; }

        /* BOTTOM SYSTEM STATUS BAR */
        .system-status-bar {
            background: #040814;
            height: 28px;
            padding: 0 20px;
            border-top: 1px solid var(--panel-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 11px;
            color: var(--text-muted);
            z-index: 100;
        }
        .status-dot-live {
            width: 7px; height: 7px;
            background: #10b981;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 6px #10b981;
        }

        /* SCROLLBAR STYLING */
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 2px; }
        ::-webkit-scrollbar-thumb:hover { background: #334155; }
    </style>
</head>
<body>

    <!-- HEADER -->
    <header>
        <div class="brand-container">
            <div class="brand-logo">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            </div>
            <div>
                <div class="brand-title">CRIMENET <span>// Investigator Intelligence Lab</span></div>
                <div class="brand-sub">IDENTIFY • CONNECT • DISRUPT</div>
            </div>
        </div>

        <div class="header-right">
            <div class="search-box">
                <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
                <input type="text" id="global-search" placeholder="Search node, name, ID..." onkeypress="handleSearch(event)">
            </div>
            <div style="position:relative; cursor:pointer; color:var(--text-secondary); display:flex; align-items:center;" title="System Notifications">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>
                <span style="position:absolute; top:-4px; right:-6px; background:#ef4444; color:#fff; font-size:9px; font-weight:700; border-radius:50%; width:14px; height:14px; display:flex; align-items:center; justify-content:center;">3</span>
            </div>
            <button class="header-btn" onclick="resetConcentricLayout()" title="Reset Concentric View">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
                Reset Layout
            </button>
            <button class="header-btn" onclick="smoothFit();" title="Fit Viewport">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>
                Fit Graph
            </button>
        </div>
    </header>

    <!-- WORKSPACE -->
    <div class="workspace">

        <!-- LEFT PANEL -->
        <div class="panel-left">
            <div>
                <div class="panel-sec-title" onclick="toggleSection(this)">
                    <span>NETWORK OVERVIEW</span>
                    <svg class="chevron-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m18 15-6-6-6 6"/></svg>
                </div>
                <div class="sec-content card-stat">
                    <div class="stat-row">
                        <div class="stat-label">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                            Total Person Nodes
                        </div>
                        <div class="stat-value" id="stat-total-nodes">--</div>
                    </div>
                    <div class="stat-row">
                        <div class="stat-label">
                            <span class="stat-dot" style="background: var(--layer-red);"></span>
                            Layer 1 (Direct Associates)
                        </div>
                        <div class="stat-value" id="stat-layer1-nodes">--</div>
                    </div>
                    <div class="stat-row">
                        <div class="stat-label">
                            <span class="stat-dot" style="background: var(--layer-yellow);"></span>
                            Layer 2 (Broader Network)
                        </div>
                        <div class="stat-value" id="stat-layer2-nodes">--</div>
                    </div>
                    <div class="stat-row">
                        <div class="stat-label">
                            <span class="stat-dot" style="background: var(--layer-green);"></span>
                            Layer 3 (Extended Network)
                        </div>
                        <div class="stat-value" id="stat-layer3-nodes">--</div>
                    </div>
                </div>
            </div>

            <div>
                <div class="panel-sec-title" onclick="toggleSection(this)">
                    <span>CASE ANCHOR</span>
                    <svg class="chevron-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m18 15-6-6-6 6"/></svg>
                </div>
                <div class="sec-content profile-card">
                    <div class="profile-avatar" style="border-color: #ffffff; color: #ffffff; background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, #0f172a 100%); box-shadow: 0 0 12px rgba(255,255,255,0.25);">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                    </div>
                    <div class="profile-info">
                        <h4 id="subject-card-name">--</h4>
                        <p id="subject-card-id">ID: -- (LOCKED CENTER)</p>
                        <p>CASE ANCHOR</p>
                        <p style="font-size:10px; color:var(--text-muted); margin-top:2px;">Role: Victim</p>
                        <div class="pill-badge pill-white">CONFIRMED VICTIM</div>
                    </div>
                </div>
            </div>

            <div>
                <div class="panel-sec-title" onclick="toggleSection(this)">
                    <span>GRAPH INTELLIGENCE CONTROLS</span>
                    <svg class="chevron-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m18 15-6-6-6 6"/></svg>
                </div>
                <div class="sec-content card-stat">
                    <div class="control-group">
                        <input type="text" class="input-dark" id="path-target-input" placeholder="Search person by name or ID...">
                    </div>
                    <div class="control-group" style="margin-top:6px; margin-bottom:6px; padding: 4px 0;">
                        <div style="display:flex; justify-content:space-between; align-items:center; font-size:11px; margin-bottom:5px;">
                            <span style="color:var(--text-secondary); font-weight:500;">Layer Spacing / Network Spread</span>
                            <span id="spread-value" style="color:var(--accent-cyan); font-family:'JetBrains Mono',monospace; font-weight:600; font-size:10.5px;">100%</span>
                        </div>
                        <input type="range" id="network-spread-slider" min="50" max="180" value="100" step="1" style="width:100%; accent-color:var(--accent-cyan); cursor:pointer;" oninput="updateNetworkSpread(this.value)">
                    </div>
                    <div class="control-group" style="margin-top:2px;">
                        <button class="btn-ctrl" onclick="resetConcentricLayout()">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
                            Reset Full Graph View
                        </button>
                    </div>
                    <div class="control-group" style="margin-top:2px;">
                        <button class="btn-ctrl" onclick="findShortestPath()">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="6" cy="6" r="3"/><circle cx="18" cy="18" r="3"/><path d="M9 6h6a3 3 0 0 1 3 3v6"/></svg>
                            Find Shortest Path
                        </button>
                    </div>
                    <div class="control-group" style="margin-top:2px;">
                        <button class="btn-ctrl" style="background:rgba(16,185,129,0.1); border-color:var(--layer-green); color:var(--layer-green);" onclick="exploreNeighbors()">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="m16 12-4-4-4 4"/><path d="M12 16V8"/></svg>
                            Explore 1-Hop Neighbors
                        </button>
                    </div>
                </div>
            </div>

            <div>
                <div class="panel-sec-title" onclick="toggleSection(this)">
                    <span>CONNECTION TYPES</span>
                    <svg class="chevron-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m18 15-6-6-6 6"/></svg>
                </div>
                <div class="sec-content card-stat">
                    <div class="legend-list">
                        <div class="legend-item">
                            <div class="legend-line" style="background: var(--layer-red);"></div>
                            Direct Association
                        </div>
                        <div class="legend-item">
                            <div class="legend-line" style="background: var(--layer-yellow);"></div>
                            Indirect Association
                        </div>
                        <div class="legend-item">
                            <div class="legend-line" style="background: var(--layer-green);"></div>
                            Extended Link
                        </div>
                        <div class="legend-item">
                            <div class="legend-line" style="border-bottom: 2px dashed #64748b;"></div>
                            Possible Link
                        </div>
                    </div>
                </div>
            </div>

            <div>
                <div class="panel-sec-title" onclick="toggleSection(this)">
                    <span>ANALYTICAL LAYERS LEGEND</span>
                    <svg class="chevron-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m18 15-6-6-6 6"/></svg>
                </div>
                <div class="sec-content card-stat">
                    <div class="layer-row">
                        <span class="ring-indicator" style="border-color: #ef4444; background: rgba(239,68,68,0.25);"></span>
                        <span><strong>Layer 1</strong> — Direct Associates</span>
                    </div>
                    <div class="layer-row">
                        <span class="ring-indicator" style="border-color: #f59e0b; background: rgba(245,158,11,0.25);"></span>
                        <span><strong>Layer 2</strong> — Broader Network</span>
                    </div>
                    <div class="layer-row">
                        <span class="ring-indicator" style="border-color: #10b981; background: rgba(16,185,129,0.25);"></span>
                        <span><strong>Layer 3</strong> — Extended Network</span>
                    </div>
                    <div class="disclaimer-sub" style="margin-top: 6px;">Colors indicate analytical relationship proximity and priority.</div>
                </div>
            </div>

            <div class="panel-footer">
                <span>Criminal Network Map</span>
                <span>AI-Powered Intelligence</span>
            </div>
        </div>

        <!-- CENTER GRAPH -->
        <div class="panel-center">
            <div id="cy-wrapper">
                <svg id="glow-overlay" width="100%" height="100%" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 1;">
                    <defs>
                        <!-- Enhanced multi-stage glow filters for high vibrancy atmospheric neon aura -->
                        <filter id="glow-red" x="-50%" y="-50%" width="200%" height="200%">
                            <feGaussianBlur stdDeviation="4" result="blur1" />
                            <feGaussianBlur stdDeviation="12" result="blur2" />
                            <feGaussianBlur stdDeviation="24" result="blur3" />
                            <feMerge>
                                <feMergeNode in="blur3" />
                                <feMergeNode in="blur2" />
                                <feMergeNode in="blur1" />
                                <feMergeNode in="SourceGraphic" />
                            </feMerge>
                        </filter>

                        <filter id="glow-yellow" x="-50%" y="-50%" width="200%" height="200%">
                            <feGaussianBlur stdDeviation="5" result="blur1" />
                            <feGaussianBlur stdDeviation="14" result="blur2" />
                            <feGaussianBlur stdDeviation="28" result="blur3" />
                            <feMerge>
                                <feMergeNode in="blur3" />
                                <feMergeNode in="blur2" />
                                <feMergeNode in="blur1" />
                                <feMergeNode in="SourceGraphic" />
                            </feMerge>
                        </filter>

                        <filter id="glow-green" x="-50%" y="-50%" width="200%" height="200%">
                            <feGaussianBlur stdDeviation="5" result="blur1" />
                            <feGaussianBlur stdDeviation="14" result="blur2" />
                            <feGaussianBlur stdDeviation="30" result="blur3" />
                            <feMerge>
                                <feMergeNode in="blur3" />
                                <feMergeNode in="blur2" />
                                <feMergeNode in="blur1" />
                                <feMergeNode in="SourceGraphic" />
                            </feMerge>
                        </filter>

                        <!-- Wide ambient atmospheric aura filter -->
                        <filter id="glow-ambient" x="-60%" y="-60%" width="220%" height="220%">
                            <feGaussianBlur stdDeviation="32" result="blur" />
                            <feMerge>
                                <feMergeNode in="blur" />
                            </feMerge>
                        </filter>

                        <!-- Radial core gradient for center case anchor (white / neutral) -->
                        <radialGradient id="centerWhiteGlow" cx="50%" cy="50%" r="50%">
                            <stop offset="0%" stop-color="#ffffff" stop-opacity="0.55"/>
                            <stop offset="35%" stop-color="#ffffff" stop-opacity="0.22"/>
                            <stop offset="70%" stop-color="#ffffff" stop-opacity="0.06"/>
                            <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
                        </radialGradient>
                    </defs>
                    <g id="concentric-rings-group" style="pointer-events: none;"></g>
                </svg>
                <div id="cy"></div>
            </div>

            <!-- FLOATING BOTTOM-RIGHT DOCK (MINIMAP) -->
            <div class="workspace-bottom-right-dock">
                <div class="dock-card minimap-container">
                    <h4>NETWORK MINIMAP</h4>
                    <div style="position: relative; width: 100%; display: flex; align-items: center; justify-content: center;">
                        <div class="compass-overlay">N<br>W + E<br>S</div>
                        <svg class="minimap-svg" viewBox="0 0 100 100">
                            <circle cx="50" cy="50" r="14" fill="none" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="2 2"/>
                            <circle cx="50" cy="50" r="26" fill="none" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="2 2"/>
                            <circle cx="50" cy="50" r="38" fill="none" stroke="#10b981" stroke-width="1.5" stroke-dasharray="2 2"/>
                            <circle cx="50" cy="50" r="4.5" fill="#ffffff"/>
                        </svg>
                        <div class="zoom-controls">
                            <button class="zoom-btn" onclick="smoothZoom(1.25);" title="Zoom In">+</button>
                            <button class="zoom-btn" onclick="smoothZoom(0.8);" title="Zoom Out">-</button>
                            <button class="zoom-btn" onclick="resetConcentricLayout();" title="Reset Concentric View">⛶</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- RIGHT INSPECTOR PANEL -->
        <div class="panel-right">
            <!-- RAI NOTICE -->
            <div class="rai-alert">
                <svg class="rai-alert-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/></svg>
                <div class="rai-alert-text">
                    <h5>Analytical Prioritization Applied</h5>
                    <p>Nodes are layered by relationship proximity and analytical priority. Experimental analytical prioritization score. Not a probability of guilt.</p>
                </div>
            </div>

            <!-- NODE / RELATIONSHIP DETAILS -->
            <div>
                <div class="panel-sec-title" onclick="toggleSection(this)">
                    <span>NODE / RELATIONSHIP INSPECTOR</span>
                    <svg class="chevron-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m18 15-6-6-6 6"/></svg>
                </div>
                <div class="sec-content" id="inspector-content">
                    <div class="inspector-card" id="inspector-initial-placeholder" style="text-align: center; padding: 26px 14px; color: var(--text-muted);">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin: 0 auto 10px auto; display: block; color: var(--accent-cyan);"><circle cx="12" cy="12" r="10"/><path d="m12 16 4-4-4-4"/><path d="M8 12h8"/></svg>
                        <p style="font-size: 11px; color: var(--text-secondary); line-height: 1.4;">Loading case anchor details from backend...</p>
                    </div>
                </div>
            </div>

            <!-- LAYER FILTERS (IMPORTANT NEW INTERACTIVE CONTROL) -->
            <div>
                <div class="panel-sec-title" onclick="toggleSection(this)">
                    <span style="display:flex; align-items:center; gap:6px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>
                        LAYER FILTERS
                    </span>
                    <svg class="chevron-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m18 15-6-6-6 6"/></svg>
                </div>
                <div class="sec-content card-stat">
                    <div class="layer-filter-grid">
                        <button class="btn-filter" id="btn-filter-l1" onclick="setLayerFilter(1)">
                            <span class="stat-dot" style="background: var(--layer-red);"></span>
                            Layer 1
                        </button>
                        <button class="btn-filter" id="btn-filter-l2" onclick="setLayerFilter(2)">
                            <span class="stat-dot" style="background: var(--layer-yellow);"></span>
                            Layer 2
                        </button>
                        <button class="btn-filter" id="btn-filter-l3" onclick="setLayerFilter(3)">
                            <span class="stat-dot" style="background: var(--layer-green);"></span>
                            Layer 3
                        </button>
                        <button class="btn-filter active" id="btn-filter-all" onclick="setLayerFilter(null)">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/></svg>
                            Show All
                        </button>
                    </div>
                    <p style="font-size:10px; color:var(--text-muted); line-height:1.3; margin-top:2px;">
                        Click a layer to highlight only that network. Other nodes will be dimmed.
                    </p>
                </div>
            </div>

        </div>
    </div>

    <!-- BOTTOM SYSTEM STATUS BAR -->
    <div class="system-status-bar">
        <div>Criminal Network Map &nbsp;|&nbsp; AI-Powered Intelligence &nbsp;|&nbsp; Law Enforcement Use Only</div>
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="display: flex; align-items: center; gap: 5px;"><span class="status-dot-live"></span> Live</span>
            <span>Kùzu Graph</span>
            <span>CCC Scorer</span>
            <span>Evidence Contract v1</span>
        </div>
    </div>

    <!-- GRAPH & INTERACTIVITY LOGIC -->
    <script>
        let cy;
        let selectedTargetId = 'CAN-PER-0001';
        let primaryId = 'CAN-PER-0001';
        let originalPositions = {};
        let activeLayerFilter = null; // null (all) or 1, 2, 3
        let cachedGraphData = null;

        // Baseline concentric radii & bounds for network spread scaling
        let currentCenterX = 0;
        let currentCenterY = 0;
        let baselinePolar = {};
        const baselineNominalRadii = { 0: 0, 1: 160, 2: 295, 3: 430 };
        const baselineLayerBounds = {
            1: { min: 110, max: 220 }, // Safe distance from center subject (32px + 22px + 56px clearance = 110px)
            2: { min: 225, max: 360 }, // Ring 2 band
            3: { min: 365, max: 520 }  // Ring 3 band
        };
        let nominalRadii = { 0: 0, 1: 160, 2: 295, 3: 430 };
        let layerBounds = {
            1: { min: 110, max: 220 },
            2: { min: 225, max: 360 },
            3: { min: 365, max: 520 }
        };
        let currentScale = 1.0;

        // Person silhouette icon SVG for Cytoscape node background
        const personIconSvg = 'data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%220%200%2024%2024%22%20width%3D%2224%22%20height%3D%2224%22%3E%3Ccircle%20cx%3D%2212%22%20cy%3D%227.2%22%20r%3D%223.8%22%20fill%3D%22%23ffffff%22/%3E%3Cpath%20d%3D%22M12%2012.8c-3.8%200-7%201.9-7.2%204.4v1.3c0%20.3.2.5.5.5h13.4c.3%200%20.5-.2.5-.5v-1.3c-.2-2.5-3.4-4.4-7.2-4.4z%22%20fill%3D%22%23ffffff%22/%3E%3C/svg%3E';

        function toggleSection(headerEl) {
            const content = headerEl.nextElementSibling;
            const chevron = headerEl.querySelector('.chevron-icon');
            if (!content) return;
            if (content.style.display === 'none') {
                content.style.display = '';
                if (chevron) chevron.style.transform = 'rotate(0deg)';
            } else {
                content.style.display = 'none';
                if (chevron) chevron.style.transform = 'rotate(180deg)';
            }
        }

        async function loadGraph() {
            const res = await fetch('/api/graph/overview');
            const data = await res.json();
            cachedGraphData = data;
            
            buildConcentricVisualization(primaryId);
        }

        function buildConcentricVisualization(targetSubjectId) {
            if (!cachedGraphData) return;
            primaryId = targetSubjectId;
            selectedTargetId = targetSubjectId;

            // Filter to Human Contact Network only (Person nodes only)
            const personNodes = cachedGraphData.nodes.filter(n => n.entity_type === 'Person');
            const personNodeIds = new Set(personNodes.map(n => n.id));
            const personEdges = cachedGraphData.edges.filter(e => personNodeIds.has(e.source) && personNodeIds.has(e.target));

            // Dynamic Concentric BFS Calculation from current targetSubjectId
            const layerMap = {};
            layerMap[primaryId] = 0;

            const adj = {};
            personEdges.forEach(e => {
                adj[e.source] = adj[e.source] || [];
                adj[e.target] = adj[e.target] || [];
                adj[e.source].push(e.target);
                adj[e.target].push(e.source);
            });

            const queue = [primaryId];
            while (queue.length > 0) {
                const curr = queue.shift();
                const currLayer = layerMap[curr];
                (adj[curr] || []).forEach(nbr => {
                    if (layerMap[nbr] === undefined) {
                        layerMap[nbr] = currLayer + 1;
                        queue.push(nbr);
                    }
                });
            }

            // Group nodes by layer
            const layerNodes = { 0: [], 1: [], 2: [], 3: [] };
            personNodes.forEach(n => {
                const rawDist = layerMap[n.id];
                const layer = (rawDist === undefined) ? 3 : Math.min(rawDist, 3);
                layerNodes[layer].push(n);
            });

            // Update Left and Right UI counters with 100% real dynamic data
            document.getElementById('stat-total-nodes').innerText = personNodes.length;
            document.getElementById('stat-layer1-nodes').innerText = layerNodes[1].length;
            document.getElementById('stat-layer2-nodes').innerText = layerNodes[2].length;
            document.getElementById('stat-layer3-nodes').innerText = layerNodes[3].length;

            const primaryNode = personNodes.find(n => n.id === primaryId) || { label: primaryId };
            document.getElementById('subject-card-name').innerText = primaryNode.label;
            document.getElementById('subject-card-id').innerText = `ID: ${primaryId} (LOCKED CENTER)`;

            // Concentric Polar Layout Calculation
            const cyContainer = document.getElementById('cy');
            const width = cyContainer.clientWidth || 900;
            const height = cyContainer.clientHeight || 700;
            const cx = width / 2;
            const cyPos = height / 2;
            currentCenterX = cx;
            currentCenterY = cyPos;

            // Reset baseline polar coordinates and slider to 100%
            baselinePolar = {};
            currentScale = 1.0;
            const spreadSlider = document.getElementById('network-spread-slider');
            if (spreadSlider) spreadSlider.value = 100;
            const spreadValEl = document.getElementById('spread-value');
            if (spreadValEl) spreadValEl.innerText = '100%';

            originalPositions = {};
            const elements = [];

            // Add Nodes with initial concentric coordinates
            Object.keys(layerNodes).forEach(lStr => {
                const layer = parseInt(lStr);
                const nodes = layerNodes[layer];
                const R = baselineNominalRadii[layer];
                const count = nodes.length;

                nodes.forEach((n, idx) => {
                    let posX = cx;
                    let posY = cyPos;
                    let angle = 0;
                    let R_actual = 0;
                    if (layer > 0 && count > 0) {
                        angle = (idx / count) * 2 * Math.PI - (Math.PI / 2);
                        R_actual = R;
                        posX = cx + R * Math.cos(angle);
                        posY = cyPos + R * Math.sin(angle);
                    }

                    baselinePolar[n.id] = { radius: R_actual, angle: angle };
                    originalPositions[n.id] = { x: posX, y: posY };

                    let nodeColor = '#38bdf8';
                    let borderColor = '#ffffff';
                    if (layer === 0) { nodeColor = '#ffffff'; borderColor = '#ffffff'; }
                    else if (layer === 1) { nodeColor = '#ef4444'; borderColor = '#ef4444'; }
                    else if (layer === 2) { nodeColor = '#f59e0b'; borderColor = '#f59e0b'; }
                    else if (layer === 3) { nodeColor = '#10b981'; borderColor = '#10b981'; }

                    const isPrimary = (n.id === primaryId);

                    elements.push({
                        data: {
                            id: n.id,
                            label: isPrimary ? `${n.label}\\n(${n.id})\\n[CONFIRMED VICTIM]` : `${n.label}`,
                            layer: layer,
                            color: nodeColor,
                            borderColor: borderColor,
                            raw: n
                        },
                        position: { x: posX, y: posY },
                        locked: isPrimary,       // ONLY Central case anchor is LOCKED at center
                        grabbable: !isPrimary    // All surrounding nodes are FREELY DRAGGABLE
                    });
                });
            });

            // Add Edges with distinct prominence for connections to Vikram Singh
            personEdges.forEach(e => {
                const isDirect = (e.source === primaryId || e.target === primaryId);
                const srcLayer = layerMap[e.source] !== undefined ? layerMap[e.source] : 3;
                const tgtLayer = layerMap[e.target] !== undefined ? layerMap[e.target] : 3;
                const maxLayer = Math.max(srcLayer, tgtLayer);

                let edgeColor = '#10b981';
                let edgeWidth = 1.4;
                let edgeOpacity = 0.55;

                if (isDirect || maxLayer <= 1) {
                    edgeColor = '#ef4444';
                    edgeWidth = 2.5;
                    edgeOpacity = 0.85;
                } else if (maxLayer === 2) {
                    edgeColor = '#f59e0b';
                    edgeWidth = 1.8;
                    edgeOpacity = 0.7;
                }

                elements.push({
                    data: {
                        id: e.id,
                        source: e.source,
                        target: e.target,
                        label: `${e.relationship_type}`,
                        color: edgeColor,
                        width: edgeWidth,
                        opacity: edgeOpacity,
                        isDirectToPrimary: isDirect ? 1 : 0,
                        ccc_score: e.ccc_score,
                        raw: e
                    }
                });
            });

            // Initialize Cytoscape with FULL drag/zoom/pan interaction enabled
            cy = cytoscape({
                container: cyContainer,
                elements: elements,
                style: [
                    {
                        selector: 'node',
                        style: {
                            'background-color': '#070e1f',
                            'border-width': '2.5px',
                            'border-color': 'data(borderColor)',
                            'background-image': personIconSvg,
                            'background-fit': 'none',
                            'background-width': '52%',
                            'background-height': '52%',
                            'background-position-x': '50%',
                            'background-position-y': '50%',
                            'background-clip': 'node',
                            'background-opacity': 1,
                            'label': 'data(label)',
                            'color': '#f8fafc',
                            'font-size': '10px',
                            'font-weight': '600',
                            'text-valign': 'bottom',
                            'text-margin-y': '6px',
                            'text-halign': 'center',
                            'text-wrap': 'wrap',
                            'width': '40px',
                            'height': '40px',
                            'transition-property': 'background-color, border-color, width, height, opacity',
                            'transition-duration': '0.2s'
                        }
                    },
                    {
                        selector: 'node[layer = 0]',
                        style: {
                            'width': '66px',
                            'height': '66px',
                            'border-width': '3.5px',
                            'border-color': '#ffffff',
                            'background-color': '#0f172a',
                            'background-image': personIconSvg,
                            'background-fit': 'none',
                            'background-width': '50%',
                            'background-height': '50%',
                            'background-position-x': '50%',
                            'background-position-y': '50%',
                            'background-clip': 'node',
                            'background-opacity': 1,
                            'font-size': '10.5px',
                            'font-weight': '700',
                            'color': '#ffffff',
                            'text-margin-y': '8px',
                            'z-index': 100
                        }
                    },
                    {
                        selector: 'node[layer = 1]',
                        style: {
                            'width': '44px',
                            'height': '44px',
                            'border-width': '2.5px',
                            'border-color': '#ef4444',
                            'background-color': '#1e0c10',
                            'background-image': personIconSvg,
                            'background-fit': 'none',
                            'background-width': '54%',
                            'background-height': '54%',
                            'background-position-x': '50%',
                            'background-position-y': '50%',
                            'background-clip': 'node',
                            'background-opacity': 1,
                            'font-size': '10px',
                            'font-weight': '600',
                            'color': '#fecaca',
                            'text-margin-y': '6px',
                            'z-index': 90
                        }
                    },
                    {
                        selector: 'node[layer = 2]',
                        style: {
                            'width': '42px',
                            'height': '42px',
                            'border-width': '2.5px',
                            'border-color': '#f59e0b',
                            'background-color': '#1d170a',
                            'background-image': personIconSvg,
                            'background-fit': 'none',
                            'background-width': '54%',
                            'background-height': '54%',
                            'background-position-x': '50%',
                            'background-position-y': '50%',
                            'background-clip': 'node',
                            'background-opacity': 1,
                            'font-size': '9.5px',
                            'font-weight': '600',
                            'color': '#fef3c7',
                            'text-margin-y': '6px',
                            'z-index': 80
                        }
                    },
                    {
                        selector: 'node[layer = 3]',
                        style: {
                            'width': '38px',
                            'height': '38px',
                            'border-width': '2.5px',
                            'border-color': '#10b981',
                            'background-color': '#081a14',
                            'background-image': personIconSvg,
                            'background-fit': 'none',
                            'background-width': '54%',
                            'background-height': '54%',
                            'background-position-x': '50%',
                            'background-position-y': '50%',
                            'background-clip': 'node',
                            'background-opacity': 1,
                            'font-size': '9px',
                            'font-weight': '600',
                            'color': '#d1fae5',
                            'text-margin-y': '6px',
                            'z-index': 70
                        }
                    },
                    {
                        selector: 'edge',
                        style: {
                            'width': 'data(width)',
                            'line-color': 'data(color)',
                            'target-arrow-color': 'data(color)',
                            'target-arrow-shape': 'triangle',
                            'arrow-scale': 0.8,
                            'curve-style': 'bezier',
                            'opacity': 'data(opacity)'
                        }
                    },
                    {
                        selector: 'edge[isDirectToPrimary = 1]',
                        style: {
                            'width': 2.5,
                            'line-color': '#ef4444',
                            'target-arrow-color': '#ef4444',
                            'target-arrow-shape': 'triangle',
                            'arrow-scale': 0.9,
                            'opacity': 0.85,
                            'z-index': 95
                        }
                    },
                    {
                        selector: ':selected',
                        style: {
                            'border-width': '4px',
                            'border-color': '#00f0ff',
                            'opacity': 1.0,
                            'z-index': 200
                        }
                    },
                    {
                        selector: '.faded',
                        style: {
                            'opacity': 0.12
                        }
                    },
                    {
                        selector: '.highlighted',
                        style: {
                            'opacity': 1.0,
                            'border-width': '3.5px',
                            'border-color': '#00f0ff',
                            'line-color': '#00f0ff',
                            'target-arrow-color': '#00f0ff',
                            'z-index': 150
                        }
                    },
                    {
                        selector: '.layer-dimmed',
                        style: {
                            'opacity': 0.12,
                            'z-index': 10
                        }
                    },
                    {
                        selector: '.layer-focused',
                        style: {
                            'opacity': 1.0,
                            'z-index': 100
                        }
                    }
                ],
                layout: { name: 'preset' },
                minZoom: 0.2,
                maxZoom: 4.0,
                zoomingEnabled: true,
                userZoomingEnabled: false, // Disables jerky default wheel steps in favor of smooth easing
                panningEnabled: true,
                userPanningEnabled: true,
                autolock: false,
                autoungrabify: false
            });

            // Initialize smooth mouse wheel zoom with requestAnimationFrame lerp easing
            initSmoothWheelZoom();

            // Explicitly lock primary subject and unlock surrounding nodes
            cy.nodes(`[id = "${primaryId}"]`).lock().ungrabify();
            cy.nodes(`[id != "${primaryId}"]`).unlock().grabify();

            // CRITICAL: LAYER-AWARE DRAG BOUNDARIES (Clamping nodes to their analytical zone)
            cy.on('drag', 'node', function(evt) {
                const node = evt.target;
                const layer = node.data('layer');
                if (!layer || layer === 0) return; // Subject is locked

                const bounds = layerBounds[layer];
                if (!bounds) return;

                const pos = node.position();
                const dx = pos.x - cx;
                const dy = pos.y - cyPos;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < bounds.min || dist > bounds.max) {
                    const clampedDist = Math.max(bounds.min, Math.min(bounds.max, dist));
                    const angle = Math.atan2(dy, dx);
                    node.position({
                        x: cx + clampedDist * Math.cos(angle),
                        y: cyPos + clampedDist * Math.sin(angle)
                    });
                }
            });

            // Render Concentric Glowing Rings in SVG overlay
            renderSVGRings(cx, cyPos, nominalRadii);

            // Sync SVG ring position on every Cytoscape pan, zoom, and viewport resize
            cy.on('pan zoom resize', syncSvgTransform);

            // Background Tap Listener (Clear selection / restore active layer filter)
            cy.on('tap', function(evt) {
                if (evt.target === cy) {
                    cy.elements().removeClass('faded highlighted');
                    if (activeLayerFilter !== null) {
                        applyLayerFilter();
                    }
                }
            });

            // Node Tap Listener (Highlight neighborhood + Inspector update while preserving layer filter)
            cy.on('tap', 'node', function(evt) {
                const node = evt.target;
                selectedTargetId = node.id();
                
                cy.elements().removeClass('faded highlighted');
                
                // If a layer filter is active, maintain it while highlighting direct neighborhood
                if (activeLayerFilter !== null) {
                    applyLayerFilter();
                } else {
                    cy.elements().addClass('faded');
                }
                
                node.closedNeighborhood().removeClass('faded layer-dimmed').addClass('highlighted');
                fetchEntityDetails(selectedTargetId);
            });

            // Edge Tap Listener
            cy.on('tap', 'edge', function(evt) {
                const edge = evt.target;
                const edgeId = edge.id();
                selectedTargetId = edgeId;
                
                cy.elements().removeClass('faded highlighted');
                cy.elements().addClass('faded');
                edge.removeClass('faded layer-dimmed').addClass('highlighted');
                edge.connectedNodes().removeClass('faded layer-dimmed').addClass('highlighted');

                fetchRelationshipDetails(edgeId);
            });

            // Initial auto-population of Primary Subject from backend
            fetchEntityDetails(primaryId);
        }

        // Renders multi-stage atmospheric radial glow and concentric guides for all layers simultaneously
        function renderSVGRings(cx, cy, radii) {
            const svgGroup = document.getElementById('concentric-rings-group');
            if (!svgGroup) return;

            const r1 = radii[1];
            const r2 = radii[2];
            const r3 = radii[3];
            const mid12 = (r1 + r2) / 2;
            const width12 = Math.max(20, r2 - r1);
            const mid23 = (r2 + r3) / 2;
            const width23 = Math.max(20, r3 - r2);
            const scale = r1 / baselineNominalRadii[1];

            // Generate 8 radar spoke lines connecting center outward through all layers
            let spokesHtml = '';
            for (let deg = 0; deg < 360; deg += 45) {
                const rad = (deg * Math.PI) / 180;
                const x1 = cx + 55 * Math.cos(rad);
                const y1 = cy + 55 * Math.sin(rad);
                const x2 = cx + (r3 + 35) * Math.cos(rad);
                const y2 = cy + (r3 + 35) * Math.sin(rad);
                spokesHtml += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="rgba(0, 240, 255, 0.14)" stroke-width="1" stroke-dasharray="2 6" style="pointer-events:none;" />`;
            }

            svgGroup.innerHTML = `
                <!-- RADAR COMPASS SPOKES -->
                ${spokesHtml}
                <!-- Extended axial crosshair lines -->
                <line x1="${cx - r3 - 40}" y1="${cy}" x2="${cx + r3 + 40}" y2="${cy}" stroke="rgba(0, 240, 255, 0.10)" stroke-width="1" stroke-dasharray="3 8" style="pointer-events:none;" />
                <line x1="${cx}" y1="${cy - r3 - 40}" x2="${cx}" y2="${cy + r3 + 40}" stroke="rgba(0, 240, 255, 0.10)" stroke-width="1" stroke-dasharray="3 8" style="pointer-events:none;" />

                <!-- ========================================================== -->
                <!-- LAYER 3: OUTERMOST EXTENDED NETWORK (VIBRANT NEON GREEN) -->
                <!-- ========================================================== -->
                <!-- Wide ambient atmospheric aura band (between L2 and L3) -->
                <circle cx="${cx}" cy="${cy}" r="${mid23}" fill="none" stroke="rgba(16, 185, 129, 0.14)" stroke-width="${width23}" filter="url(#glow-ambient)" style="pointer-events:none;" />
                <!-- Intense neon outer glow halo -->
                <circle cx="${cx}" cy="${cy}" r="${r3}" fill="none" stroke="#10b981" stroke-width="20" opacity="0.65" filter="url(#glow-green)" style="pointer-events:none;" />
                <!-- Sharp dashed main orbit line -->
                <circle cx="${cx}" cy="${cy}" r="${r3}" fill="none" stroke="#10b981" stroke-width="2.5" stroke-dasharray="10 8" opacity="0.95" style="pointer-events:none;" />
                <!-- Outer guide ring -->
                <circle cx="${cx}" cy="${cy}" r="${r3 + 24 * scale}" fill="none" stroke="#10b981" stroke-width="1.2" stroke-dasharray="4 10" opacity="0.30" style="pointer-events:none;" />

                <!-- ========================================================== -->
                <!-- LAYER 2: MIDDLE BROADER NETWORK (VIBRANT AMBER / GOLD) -->
                <!-- ========================================================== -->
                <!-- Wide ambient atmospheric aura band (between L1 and L2) -->
                <circle cx="${cx}" cy="${cy}" r="${mid12}" fill="none" stroke="rgba(245, 158, 11, 0.16)" stroke-width="${width12}" filter="url(#glow-ambient)" style="pointer-events:none;" />
                <!-- Intense golden-yellow glow halo -->
                <circle cx="${cx}" cy="${cy}" r="${r2}" fill="none" stroke="#f59e0b" stroke-width="18" opacity="0.70" filter="url(#glow-yellow)" style="pointer-events:none;" />
                <!-- Sharp dashed main orbit line -->
                <circle cx="${cx}" cy="${cy}" r="${r2}" fill="none" stroke="#f59e0b" stroke-width="2.5" stroke-dasharray="8 6" opacity="0.95" style="pointer-events:none;" />
                <!-- Outer guide ring -->
                <circle cx="${cx}" cy="${cy}" r="${r2 + 20 * scale}" fill="none" stroke="#f59e0b" stroke-width="1.2" stroke-dasharray="3 8" opacity="0.35" style="pointer-events:none;" />

                <!-- ========================================================== -->
                <!-- LAYER 1: INNER DIRECT ASSOCIATES (VIBRANT CRIMSON RED) -->
                <!-- ========================================================== -->
                <!-- Deep crimson translucent radial disk wash -->
                <circle cx="${cx}" cy="${cy}" r="${r1}" fill="rgba(239, 68, 68, 0.15)" style="pointer-events:none;" />
                <!-- Intense red glow halo -->
                <circle cx="${cx}" cy="${cy}" r="${r1}" fill="none" stroke="#ef4444" stroke-width="16" opacity="0.65" filter="url(#glow-red)" style="pointer-events:none;" />
                <!-- Sharp dashed main orbit line -->
                <circle cx="${cx}" cy="${cy}" r="${r1}" fill="none" stroke="#ef4444" stroke-width="2.2" stroke-dasharray="6 4" opacity="0.95" style="pointer-events:none;" />
                <!-- Outer guide ring -->
                <circle cx="${cx}" cy="${cy}" r="${r1 + 16 * scale}" fill="none" stroke="#ef4444" stroke-width="1.2" stroke-dasharray="2 6" opacity="0.40" style="pointer-events:none;" />

                <!-- ========================================================== -->
                <!-- CENTER CASE ANCHOR RETICLE & CORE RADIANCE (WHITE / NEUTRAL) -->
                <!-- ========================================================== -->
                <circle cx="${cx}" cy="${cy}" r="${Math.max(80, 115 * scale)}" fill="url(#centerWhiteGlow)" style="pointer-events:none;" />
                <circle cx="${cx}" cy="${cy}" r="52" fill="none" stroke="#ffffff" stroke-width="1.5" stroke-dasharray="4 4" opacity="0.65" style="pointer-events:none;" />
                <!-- Center crosshair alignment ticks -->
                <line x1="${cx - 62}" y1="${cy}" x2="${cx - 44}" y2="${cy}" stroke="#ffffff" stroke-width="2" opacity="0.75" />
                <line x1="${cx + 44}" y1="${cy}" x2="${cx + 62}" y2="${cy}" stroke="#ffffff" stroke-width="2" opacity="0.75" />
                <line x1="${cx}" y1="${cy - 62}" x2="${cx}" y2="${cy - 44}" stroke="#ffffff" stroke-width="2" opacity="0.75" />
                <line x1="${cx}" y1="${cy + 44}" x2="${cx}" y2="${cy + 62}" stroke="#ffffff" stroke-width="2" opacity="0.75" />
            `;
            syncSvgTransform();
        }

        // Synchronize SVG concentric rings with Cytoscape viewport pan and zoom
        function syncSvgTransform() {
            if (!cy) return;
            const svgGroup = document.getElementById('concentric-rings-group');
            if (!svgGroup) return;
            const pan = cy.pan();
            const zoom = cy.zoom();
            svgGroup.setAttribute('transform', `translate(${pan.x}, ${pan.y}) scale(${zoom})`);
        }

        // LAYER FILTERING: Presentation-only highlighting of selected layer
        function setLayerFilter(layer) {
            activeLayerFilter = layer;
            
            // Update button styles
            document.querySelectorAll('.btn-filter').forEach(b => b.classList.remove('active'));
            if (layer === 1) document.getElementById('btn-filter-l1').classList.add('active');
            else if (layer === 2) document.getElementById('btn-filter-l2').classList.add('active');
            else if (layer === 3) document.getElementById('btn-filter-l3').classList.add('active');
            else document.getElementById('btn-filter-all').classList.add('active');

            applyLayerFilter();
        }

        function applyLayerFilter() {
            if (!cy) return;
            cy.elements().removeClass('faded highlighted layer-dimmed layer-focused');
            
            if (activeLayerFilter === null) {
                // Show All: normal full visibility
                return;
            }

            cy.batch(() => {
                // Primary subject is always kept focused
                cy.nodes(`[id = "${primaryId}"]`).addClass('layer-focused');

                // Target layer nodes focused
                cy.nodes(`[layer = ${activeLayerFilter}]`).addClass('layer-focused');

                // Other layer nodes dimmed
                cy.nodes(`[layer != ${activeLayerFilter}][id != "${primaryId}"]`).addClass('layer-dimmed');

                // Edges touching the target layer or primary subject
                cy.edges().forEach(e => {
                    const sL = e.source().data('layer');
                    const tL = e.target().data('layer');
                    if (sL === activeLayerFilter || tL === activeLayerFilter) {
                        e.addClass('layer-focused');
                    } else {
                        e.addClass('layer-dimmed');
                    }
                });
            });
        }

        // =========================================================================
        // SMOOTH MOUSE WHEEL ZOOM & VIEWPORT EASING
        // =========================================================================
        let targetZoom = null;
        let zoomFocalPoint = null;
        let zoomRafId = null;

        function initSmoothWheelZoom() {
            const cyContainer = document.getElementById('cy');
            if (!cyContainer || cyContainer.dataset.smoothWheelAttached) return;
            cyContainer.dataset.smoothWheelAttached = 'true';

            cyContainer.addEventListener('wheel', function(e) {
                if (!cy) return;
                e.preventDefault();
                e.stopPropagation();

                const rect = cyContainer.getBoundingClientRect();
                zoomFocalPoint = {
                    x: e.clientX - rect.left,
                    y: e.clientY - rect.top
                };

                if (targetZoom === null) {
                    targetZoom = cy.zoom();
                }

                // Normalize scroll delta across devices (wheel ticks vs trackpad lines/pages)
                let dy = e.deltaY;
                if (e.deltaMode === 1) { // Line mode
                    dy *= 32;
                } else if (e.deltaMode === 2) { // Page mode
                    dy *= 100;
                }

                // Smooth exponential scaling (~8.5% change per standard wheel notch)
                const zoomFactor = Math.pow(0.9991, dy);
                targetZoom = Math.max(0.2, Math.min(4.0, targetZoom * zoomFactor));

                if (!zoomRafId) {
                    zoomRafId = requestAnimationFrame(animateSmoothWheel);
                }
            }, { passive: false });
        }

        function animateSmoothWheel() {
            if (!cy || targetZoom === null) {
                zoomRafId = null;
                return;
            }

            const currentZoom = cy.zoom();
            const diff = targetZoom - currentZoom;

            // Exponential lerp easing step (22% per animation frame for fluid glide)
            if (Math.abs(diff) > 0.0015) {
                const nextZoom = currentZoom + diff * 0.22;
                cy.zoom({
                    level: nextZoom,
                    renderedPosition: zoomFocalPoint
                });
                syncSvgTransform();
                zoomRafId = requestAnimationFrame(animateSmoothWheel);
            } else {
                cy.zoom({
                    level: targetZoom,
                    renderedPosition: zoomFocalPoint
                });
                syncSvgTransform();
                targetZoom = null;
                zoomRafId = null;
            }
        }

        function smoothZoom(factor) {
            if (!cy) return;
            if (zoomRafId) {
                cancelAnimationFrame(zoomRafId);
                zoomRafId = null;
                targetZoom = null;
            }
            const currentZoom = cy.zoom();
            const newZoom = Math.max(0.2, Math.min(4.0, currentZoom * factor));
            cy.animate({
                zoom: {
                    level: newZoom,
                    renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 }
                }
            }, {
                duration: 240,
                easing: 'ease-out-cubic'
            });
        }

        function smoothFit() {
            if (!cy) return;
            if (zoomRafId) {
                cancelAnimationFrame(zoomRafId);
                zoomRafId = null;
                targetZoom = null;
            }
            cy.animate({
                fit: { eles: cy.elements(), padding: 40 }
            }, {
                duration: 320,
                easing: 'ease-out-cubic'
            });
        }

        // =========================================================================
        // NETWORK SPREAD / LAYER SPACING SLIDER CONTROLLER
        // =========================================================================
        function updateNetworkSpread(val) {
            if (!cy) return;
            const scale = parseFloat(val) / 100.0;
            currentScale = scale;

            const spreadValEl = document.getElementById('spread-value');
            if (spreadValEl) spreadValEl.innerText = `${val}%`;

            const cx = currentCenterX;
            const cyPos = currentCenterY;

            // Proportionally update every person node's distance from center
            cy.batch(() => {
                cy.nodes().forEach(node => {
                    const id = node.id();
                    if (id === primaryId) {
                        node.position({ x: cx, y: cyPos }); // Primary subject stays locked at exact center
                        return;
                    }
                    const polar = baselinePolar[id];
                    if (polar) {
                        const newRadius = polar.radius * scale;
                        const newX = cx + newRadius * Math.cos(polar.angle);
                        const newY = cyPos + newRadius * Math.sin(polar.angle);
                        node.position({ x: newX, y: newY });
                        originalPositions[id] = { x: newX, y: newY };
                    }
                });
            });

            // Scale layer rings by the exact same factor
            const scaledRadii = {
                0: 0,
                1: baselineNominalRadii[1] * scale,
                2: baselineNominalRadii[2] * scale,
                3: baselineNominalRadii[3] * scale
            };

            // Scale layer bounds for dragging
            layerBounds[1] = { min: baselineLayerBounds[1].min * scale, max: baselineLayerBounds[1].max * scale };
            layerBounds[2] = { min: baselineLayerBounds[2].min * scale, max: baselineLayerBounds[2].max * scale };
            layerBounds[3] = { min: baselineLayerBounds[3].min * scale, max: baselineLayerBounds[3].max * scale };

            // Re-render SVG rings
            renderSVGRings(cx, cyPos, scaledRadii);
        }

        // RESET FULL GRAPH VIEW (Returns all nodes to concentric initial positions, clears filter)
        function resetConcentricLayout() {
            if (!cy) return;
            if (zoomRafId) {
                cancelAnimationFrame(zoomRafId);
                zoomRafId = null;
                targetZoom = null;
            }
            activeLayerFilter = null;
            document.querySelectorAll('.btn-filter').forEach(b => b.classList.remove('active'));
            document.getElementById('btn-filter-all').classList.add('active');

            // Reset Network Spread slider to baseline 100%
            const spreadSlider = document.getElementById('network-spread-slider');
            if (spreadSlider) spreadSlider.value = 100;
            const spreadValEl = document.getElementById('spread-value');
            if (spreadValEl) spreadValEl.innerText = '100%';

            updateNetworkSpread(100);

            cy.elements().removeClass('faded highlighted layer-dimmed layer-focused');
            // Re-enforce lock
            cy.nodes(`[id = "${primaryId}"]`).lock().ungrabify();
            cy.nodes(`[id != "${primaryId}"]`).unlock().grabify();
            smoothFit();
        }

        // Fetch Real Entity Details from backend
        async function fetchEntityDetails(id) {
            selectedTargetId = id;
            const res = await fetch(`/api/entity/${id}`);
            if (res.ok) {
                const d = await res.json();
                renderEntityInspector(d);
            }
        }

        // Fetch Real Relationship Details from backend
        async function fetchRelationshipDetails(edgeId) {
            selectedTargetId = edgeId;
            const res = await fetch(`/api/relationship/${edgeId}`);
            if (res.ok) {
                const d = await res.json();
                renderEdgeInspector(d);
            }
        }

        function renderEntityInspector(d) {
            const insp = document.getElementById('inspector-content');
            const isSubject = (d.canonical_entity_id === primaryId);
            const badgeClass = isSubject ? "pill-white" : "pill-red";
            const badgeText = isSubject ? "CONFIRMED VICTIM" : d.entity_type.toUpperCase();

            insp.innerHTML = `
                <div class="inspector-card">
                    <div class="inspector-header">
                        <div class="inspector-avatar" style="${isSubject ? 'border-color:#ffffff; color:#ffffff; background:#0f172a;' : ''}">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                        </div>
                        <div>
                            <h4 style="font-size:14px; font-weight:600; color:#fff;">${d.canonical_name}</h4>
                            <div style="display:flex; align-items:center; gap:6px; margin-top:2px;">
                                <span style="font-family:'JetBrains Mono'; font-size:11px; color:var(--text-secondary);">${d.canonical_entity_id}</span>
                                <span class="pill-badge ${badgeClass}" style="margin:0; font-size:9px;">${badgeText}</span>
                            </div>
                        </div>
                    </div>

                    <div class="prop-grid">
                        <div class="prop-item"><span class="prop-key">Entity Type:</span><span class="prop-val">${d.entity_type}</span></div>
                        <div class="prop-item"><span class="prop-key">Canonical Name:</span><span class="prop-val">${d.canonical_name}</span></div>
                        <div class="prop-item"><span class="prop-key">Case Role:</span><span class="prop-val">${isSubject ? "Case Anchor (Confirmed Victim)" : "Analytical Lead"}</span></div>
                        <div class="prop-item"><span class="prop-key">Match Confidence:</span><span class="prop-val" style="color:var(--accent-cyan);">${Math.round(d.match_confidence * 100)}%</span></div>
                        <div class="prop-item"><span class="prop-key">Match Method:</span><span class="prop-val">${d.match_method}</span></div>
                        <div class="prop-item"><span class="prop-key">Verification Status:</span><span class="pill-badge" style="background:#f59e0b22; color:#fde047; border:1px solid #f59e0b; margin:0;" id="ver-badge-status">${d.human_verification_status}</span></div>
                        <div class="prop-item"><span class="prop-key">Evidence Count:</span><span class="prop-val">${(d.source_evidence_ids || []).length}</span></div>
                        <div class="prop-item"><span class="prop-key">Last Updated:</span><span class="prop-val">2026-09-04 14:22:00</span></div>
                    </div>

                    <div class="btn-action-group">
                        <button class="btn-act btn-review-lead" onclick="verifyCurrentTarget('UNDER_REVIEW')">
                            Under Review
                        </button>
                        <button class="btn-act btn-verify-lead" onclick="verifyCurrentTarget('HUMAN_VERIFIED_LEAD')">
                            ✓ Verify Lead
                        </button>
                        <button class="btn-act btn-reject-lead" onclick="verifyCurrentTarget('REJECTED_ASSOCIATION')">
                            ✕ Reject
                        </button>
                    </div>

                    <div class="provenance-box">
                        <h5>Evidence Provenance</h5>
                        <p><strong>Observed Values:</strong> ${(d.observed_values || []).join(', ')}</p>
                        <p><strong>Source Evidence IDs:</strong> ${(d.source_evidence_ids || []).join(', ')}</p>
                    </div>
                </div>
            `;
        }

        function renderEdgeInspector(d) {
            let ringColor = 'var(--layer-green)';
            if (d.ccc_ring === 'RED') ringColor = 'var(--layer-red)';
            if (d.ccc_ring === 'YELLOW') ringColor = 'var(--layer-yellow)';

            const indicatorsHtml = (d.contributing_indicators || []).map(ind => `<li>${ind}</li>`).join('');

            const insp = document.getElementById('inspector-content');
            insp.innerHTML = `
                <div class="inspector-card">
                    <div class="inspector-header">
                        <div class="inspector-avatar" style="border-color:${ringColor}">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
                        </div>
                        <div>
                            <h4 style="font-size:14px; font-weight:600; color:#fff;">${d.relationship_type}</h4>
                            <p style="font-size:11px; color:${ringColor}; font-weight:600;">CCC RING: ${d.ccc_ring}</p>
                        </div>
                    </div>

                    <div class="prop-grid">
                        <div class="prop-item"><span class="prop-key">Association Score:</span><span class="prop-val" style="font-size:14px; color:var(--accent-cyan);">${d.association_score} / 100</span></div>
                        <div class="prop-item"><span class="prop-key">Priority Label:</span><span class="prop-val">${d.priority_label}</span></div>
                        <div class="prop-item"><span class="prop-key">Source Entity:</span><span class="prop-val">${d.source_entity}</span></div>
                        <div class="prop-item"><span class="prop-key">Target Entity:</span><span class="prop-val">${d.target_entity}</span></div>
                        <div class="prop-item"><span class="prop-key">Interaction Freq:</span><span class="prop-val">${d.interaction_frequency} interactions</span></div>
                        <div class="prop-item"><span class="prop-key">ER Confidence:</span><span class="prop-val">${Math.round(d.confidence * 100)}%</span></div>
                        <div class="prop-item"><span class="prop-key">Provenance Status:</span><span class="prop-val" style="color:var(--layer-green);">${d.provenance_status}</span></div>
                        <div class="prop-item"><span class="prop-key">Verification Status:</span><span class="pill-badge pill-red" id="ver-badge-status">${d.human_verification_status}</span></div>
                    </div>

                    <div class="btn-action-group">
                        <button class="btn-act btn-review-lead" onclick="verifyCurrentTarget('UNDER_REVIEW')">
                            Under Review
                        </button>
                        <button class="btn-act btn-verify-lead" onclick="verifyCurrentTarget('HUMAN_VERIFIED_LEAD')">
                            ✓ Verify Lead
                        </button>
                        <button class="btn-act btn-reject-lead" onclick="verifyCurrentTarget('REJECTED_ASSOCIATION')">
                            ✕ Reject
                        </button>
                    </div>

                    <div class="provenance-box">
                        <h5>Contributing Score Indicators</h5>
                        <ul style="font-size:11px; padding-left:14px; color:var(--text-secondary); line-height:1.4;">
                            ${indicatorsHtml}
                        </ul>
                    </div>

                    <div class="provenance-box">
                        <h5>Evidence Contract Traceability</h5>
                        <p><strong>Primary Artifact:</strong> ${d.source_artifact} (${d.source_format})</p>
                        <p><strong>Timestamp:</strong> ${d.timestamp}</p>
                        <p><strong>Evidence IDs:</strong> ${(d.supporting_evidence_ids || []).join(', ')}</p>
                        <button class="btn-ctrl" style="margin-top:6px; font-size:10px;" onclick="inspectEvidenceDetails('${d.supporting_evidence_id}')">
                            View Full Evidence Chain-of-Custody
                        </button>
                    </div>
                </div>
            `;
        }

        async function inspectEvidenceDetails(evidenceId) {
            const res = await fetch(`/api/evidence/${evidenceId}`);
            if (res.ok) {
                const data = await res.json();
                const rec = data.evidence_record;
                alert(
                    `EVIDENCE CHAIN OF CUSTODY:\\n\\n` +
                    `Status: ${data.traceability_status}\\n` +
                    `Evidence ID: ${rec.evidence_id}\\n` +
                    `Source Artifact: ${rec.source_artifact}\\n` +
                    `Source Format: ${rec.source_format}\\n` +
                    `SHA-256: ${rec.sha256}\\n` +
                    `Timestamp: ${rec.timestamp}\\n` +
                    `Details: ${rec.details}`
                );
            }
        }

        async function verifyCurrentTarget(status) {
            const res = await fetch('/api/verification/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ entity_id: selectedTargetId, status: status, notes: 'Recorded via CRIMENET Investigator Console' })
            });
            if (res.ok) {
                const badge = document.getElementById('ver-badge-status');
                if (badge) badge.innerText = status;
                alert(`Human Verification logged as [${status}] for ${selectedTargetId}`);
            }
        }

        async function findShortestPath() {
            const tgtInput = document.getElementById('path-target-input').value.trim();
            if (!tgtInput) {
                alert('Please enter a target suspect ID (e.g. CAN-PER-0002)');
                return;
            }
            const res = await fetch(`/api/graph/shortest_path?src_id=${primaryId}&tgt_id=${tgtInput}`);
            if (res.ok) {
                const data = await res.json();
                if (data.path_length >= 0) {
                    cy.elements().removeClass('faded highlighted');
                    cy.elements().addClass('faded');
                    data.path_nodes.forEach(nid => {
                        const ele = cy.nodes(`[id = "${nid}"]`);
                        ele.removeClass('faded').addClass('highlighted');
                    });
                    alert(`Shortest Path found (${data.path_length} hops):\\n${data.path_nodes.join(' -> ')}`);
                } else {
                    alert(`No path found between ${primaryId} and ${tgtInput}`);
                }
            }
        }

        async function exploreNeighbors() {
            if (!selectedTargetId) return;
            const res = await fetch(`/api/graph/neighbors/${selectedTargetId}?hops=1`);
            if (res.ok) {
                const data = await res.json();
                alert(`Root: ${data.root_entity_id} has ${data.neighbor_count} 1-hop neighbors:\\n${data.neighbors.map(n=>n.canonical_name).join(', ')}`);
            }
        }

        function handleSearch(evt) {
            if (evt.key === 'Enter') {
                const query = evt.target.value.trim().toLowerCase();
                if (!query) return;
                
                const found = cy.nodes().filter(n => {
                    const label = (n.data('label') || '').toLowerCase();
                    const id = (n.data('id') || '').toLowerCase();
                    return label.includes(query) || id.includes(query);
                });

                if (found.length > 0) {
                    const targetNode = found[0];
                    cy.animate({
                        center: { eles: targetNode },
                        zoom: 1.3
                    }, { duration: 500 });
                    
                    cy.elements().removeClass('faded highlighted');
                    cy.elements().addClass('faded');
                    targetNode.closedNeighborhood().removeClass('faded').addClass('highlighted');
                    
                    selectedTargetId = targetNode.id();
                    fetchEntityDetails(selectedTargetId);
                } else {
                    alert('No matching person node found in Human Contact Network.');
                }
            }
        }

        window.onload = loadGraph;
        window.onresize = () => { if (cy) { cy.fit(); syncSvgTransform(); } };
    </script>
</body>
</html>"""
    return html_content
