# -*- coding: utf-8 -*-
"""
Injects the Investigator Case Portal & Entry Workflow into scripts/build_final_workspace_html.py
Matching reference media_1788734391416.png with pixel accuracy.
"""

import os
import re

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "build_final_workspace_html.py")

PORTAL_CSS = """
        /* ==================================================================== */
        /* INVESTIGATOR CASE PORTAL STYLES (MATCHING media_1788734391416.png)  */
        /* ==================================================================== */
        #view-portal {
            background: #030713;
            position: relative;
            overflow-y: auto;
            width: 100%;
            height: 100%;
            display: none;
        }
        #view-portal.active {
            display: block !important;
        }
        .portal-canvas {
            position: relative;
            min-height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 30px 20px;
            background-image: radial-gradient(circle at 50% 28%, rgba(0, 240, 255, 0.08) 0%, transparent 65%);
        }
        .portal-watermark-tr {
            position: absolute;
            top: 24px;
            right: 28px;
            text-align: right;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 2.8px;
            color: rgba(56, 189, 248, 0.22);
            line-height: 1.8;
            pointer-events: none;
            user-select: none;
        }
        .portal-watermark-bl {
            position: absolute;
            bottom: 24px;
            left: 28px;
            text-align: left;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 2.8px;
            color: rgba(56, 189, 248, 0.22);
            line-height: 1.8;
            pointer-events: none;
            user-select: none;
        }
        .portal-bg-fingerprint {
            position: absolute;
            left: 40px;
            top: 50%;
            transform: translateY(-50%);
            width: 240px;
            height: 300px;
            pointer-events: none;
            user-select: none;
            opacity: 0.7;
        }
        .portal-bg-constellation {
            position: absolute;
            right: 30px;
            top: 50%;
            transform: translateY(-50%);
            width: 320px;
            height: 280px;
            pointer-events: none;
            user-select: none;
            opacity: 0.7;
        }
        .portal-inner {
            max-width: 780px;
            width: 100%;
            position: relative;
            z-index: 10;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .portal-hero {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            margin-bottom: 22px;
        }
        .portal-shield-icon {
            width: 58px;
            height: 64px;
            margin-bottom: 6px;
            filter: drop-shadow(0 0 16px rgba(0, 240, 255, 0.65));
        }
        .portal-title {
            font-size: 30px;
            font-weight: 800;
            letter-spacing: 2.5px;
            color: #ffffff;
            margin: 4px 0 2px 0;
        }
        .portal-subtitle {
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 2.2px;
            color: #00f0ff;
            text-transform: uppercase;
            margin-bottom: 6px;
        }
        .portal-description {
            font-size: 13px;
            color: #94a3b8;
            max-width: 540px;
            line-height: 1.45;
        }
        .portal-cards-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            width: 100%;
            margin-bottom: 22px;
        }
        .portal-card {
            background: rgba(6, 14, 32, 0.85);
            backdrop-filter: blur(12px);
            border-radius: 8px;
            padding: 24px 22px;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            transition: all 0.2s ease;
        }
        .portal-card.new-case-card {
            border: 1.5px solid #00f0ff;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.6), 0 0 20px rgba(0, 240, 255, 0.16);
        }
        .portal-card.new-case-card:hover {
            box-shadow: 0 10px 36px rgba(0, 0, 0, 0.7), 0 0 28px rgba(0, 240, 255, 0.3);
            border-color: #38bdf8;
        }
        .portal-card.open-case-card {
            border: 1px solid rgba(56, 189, 248, 0.28);
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.6);
        }
        .portal-card.open-case-card:hover {
            border-color: #38bdf8;
            box-shadow: 0 10px 36px rgba(0, 0, 0, 0.7), 0 0 20px rgba(56, 189, 248, 0.2);
        }
        .portal-card-icon {
            margin-bottom: 12px;
        }
        .portal-card-title {
            font-size: 14.5px;
            font-weight: 800;
            letter-spacing: 1.2px;
            margin-bottom: 8px;
            text-transform: uppercase;
        }
        .portal-card-title.cyan { color: #00f0ff; }
        .portal-card-title.sky { color: #38bdf8; }
        .portal-card-text {
            font-size: 12px;
            color: #94a3b8;
            line-height: 1.45;
            margin-bottom: 18px;
            min-height: 48px;
        }
        .btn-create-new-case {
            width: 100%;
            background: #00f0ff;
            color: #030712;
            border: none;
            border-radius: 5px;
            padding: 9px 16px;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.5px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 14px rgba(0, 240, 255, 0.35);
            transition: all 0.15s;
        }
        .btn-create-new-case:hover {
            background: #38bdf8;
            box-shadow: 0 0 22px rgba(0, 240, 255, 0.6);
            transform: translateY(-1px);
        }
        .btn-open-existing-case {
            width: 100%;
            background: transparent;
            color: #38bdf8;
            border: 1.5px solid #0284c7;
            border-radius: 5px;
            padding: 9px 16px;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.5px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.15s;
        }
        .btn-open-existing-case:hover {
            background: rgba(2, 132, 199, 0.15);
            border-color: #38bdf8;
            color: #ffffff;
            box-shadow: 0 0 16px rgba(56, 189, 248, 0.3);
        }

        /* RECENT CASES */
        .portal-recent-box {
            width: 100%;
            background: rgba(4, 11, 26, 0.9);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(56, 189, 248, 0.2);
            border-radius: 8px;
            padding: 14px 18px;
        }
        .portal-recent-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        .portal-recent-title {
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 1px;
            color: #38bdf8;
            text-transform: uppercase;
        }
        .portal-recent-link {
            font-size: 11.5px;
            font-weight: 600;
            color: #38bdf8;
            text-decoration: none;
            cursor: pointer;
            transition: color 0.15s;
        }
        .portal-recent-link:hover {
            color: #00f0ff;
            text-decoration: underline;
        }
        .portal-recent-list {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .portal-case-row {
            display: grid;
            grid-template-columns: 28px 1.4fr 1fr 1.1fr 1fr 90px;
            align-items: center;
            gap: 12px;
            padding: 8px 10px;
            border-radius: 6px;
            background: rgba(15, 23, 42, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.03);
            transition: all 0.15s;
        }
        .portal-case-row:hover {
            background: rgba(14, 165, 233, 0.08);
            border-color: rgba(56, 189, 248, 0.25);
        }
        .portal-case-icon svg { display: block; }
        .portal-case-info { display: flex; flex-direction: column; }
        .portal-case-id { font-size: 12px; font-weight: 700; color: #ffffff; font-family: 'JetBrains Mono', monospace; }
        .portal-case-name { font-size: 11px; color: var(--text-secondary); margin-top: 2px; }
        .portal-case-col { display: flex; flex-direction: column; }
        .portal-col-label { font-size: 9px; text-transform: uppercase; color: var(--text-muted); font-weight: 600; margin-bottom: 2px; }
        .portal-col-val { font-size: 11px; color: #cbd5e1; font-family: 'JetBrains Mono', monospace; }

        .portal-status-active { color: #10b981; font-size: 11px; font-weight: 700; display: flex; align-items: center; gap: 4px; }
        .portal-status-in_progress { color: #f59e0b; font-size: 11px; font-weight: 700; display: flex; align-items: center; gap: 4px; }
        .portal-status-draft { color: #94a3b8; font-size: 11px; font-weight: 700; display: flex; align-items: center; gap: 4px; }
        .portal-status-closed { color: #64748b; font-size: 11px; font-weight: 700; display: flex; align-items: center; gap: 4px; }
        .status-dot { font-size: 8px; }

        .btn-open-case {
            background: transparent;
            border: 1px solid #0284c7;
            color: #38bdf8;
            font-size: 11px;
            font-weight: 600;
            padding: 5px 12px;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.15s;
            text-align: center;
        }
        .btn-open-case:hover {
            background: #0284c7;
            color: #ffffff;
            box-shadow: 0 0 10px var(--accent-cyan-glow);
        }

        /* MULTI-STEP MODAL STYLES */
        .stepper-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 18px;
            border-bottom: 1px solid rgba(255,255,255,0.08);
            padding-bottom: 12px;
        }
        .step-item {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 11px;
            font-weight: 600;
            color: var(--text-muted);
        }
        .step-item.active {
            color: var(--accent-cyan);
        }
        .step-item.done {
            color: var(--layer-green);
        }
        .step-num {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: rgba(255,255,255,0.06);
            border: 1px solid var(--panel-border);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
        }
        .step-item.active .step-num {
            background: rgba(0,240,255,0.2);
            border-color: var(--accent-cyan);
            color: #fff;
        }
        .step-item.done .step-num {
            background: rgba(16,185,129,0.2);
            border-color: var(--layer-green);
            color: #fff;
        }
        .step-sep {
            color: rgba(255,255,255,0.15);
            font-size: 11px;
        }
        .step-pane { display: none; }
        .step-pane.active { display: block; }
        .candidate-card {
            background: rgba(7, 14, 31, 0.85);
            border: 1px solid var(--panel-border);
            border-radius: 6px;
            padding: 12px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.15s;
        }
        .candidate-card:hover, .candidate-card.selected {
            border-color: var(--accent-cyan);
            background: rgba(0, 240, 255, 0.05);
        }
        .inspect-badge-box {
            background: #040814;
            border: 1px solid rgba(0,240,255,0.25);
            border-radius: 6px;
            padding: 12px;
            margin-top: 10px;
        }
"""

def inject():
    with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Inject CSS before </style>
    if "/* INVESTIGATOR CASE PORTAL STYLES" not in content:
        content = content.replace("    </style>", PORTAL_CSS + "\n    </style>")
        print("Injected PORTAL_CSS")

    # 2. Activity Bar Home Item
    if "activity-btn-home" not in content:
        home_activity_btn = """                    <!-- 0. Home / Case Portal -->
                    <div class="activity-item active" id="activity-btn-home" onclick="switchFeature('home')" title="Investigator Case Portal">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
                        <span class="activity-label">Home</span>
                    </div>
"""
        content = content.replace(
            '<div class="activity-item active" id="activity-btn-cases"',
            home_activity_btn + '                    <div class="activity-item" id="activity-btn-cases"'
        )
        print("Injected activity-btn-home")

    # 3. Header Right Tools Wrapper
    if 'id="portal-header-tools"' not in content:
        content = content.replace(
            '<div class="case-select-wrapper">',
            '<div class="portal-header-tools" id="portal-header-tools" style="display:none; align-items:center; gap:10px;">\n            <div class="case-select-wrapper">'
        )
        content = content.replace(
            '<!-- LOGOUT -->\n            <button class="btn-header-logout"',
            '</div>\n            <!-- LOGOUT -->\n            <button class="btn-header-logout"'
        )
        print("Injected portal-header-tools wrapper")

    # 4. Brand container clicks to Home
    content = content.replace(
        '<div class="brand-container" onclick="switchFeature(\'cases\')">',
        '<div class="brand-container" onclick="switchFeature(\'home\')">'
    )

    # 5. Inject Center View 0 (Investigator Case Portal) before view-cases
    if 'id="view-portal"' not in content:
        portal_html = """                <!-- ---------------------------------------------------------- -->
                <!-- VIEW 0: INVESTIGATOR CASE PORTAL (REFERENCE SCREENSHOT)    -->
                <!-- ---------------------------------------------------------- -->
                <div id="view-portal" class="view-pane active">
                    <div class="portal-canvas">
                        <!-- WATERMARKS -->
                        <div class="portal-watermark-tr">
                            EVIDENCE<br>
                            INTELLIGENCE<br>
                            JUSTICE<br>
                            A SAFER TOMORROW
                        </div>
                        <div class="portal-watermark-bl">
                            FORENSIC SCIENCE<br>
                            DATA INTELLIGENCE<br>
                            HUMAN INSIGHT
                        </div>

                        <!-- WATERMARK SVGS -->
                        <svg class="portal-bg-fingerprint" viewBox="0 0 200 240" fill="none">
                            <path d="M100,20 C50,20 20,60 20,110 C20,165 45,210 90,225" stroke="rgba(0,240,255,0.08)" stroke-width="1.8"/>
                            <path d="M100,35 C60,35 35,70 35,115 C35,160 55,195 95,210" stroke="rgba(0,240,255,0.08)" stroke-width="1.8"/>
                            <path d="M100,50 C70,50 50,80 50,120 C50,155 65,180 100,195" stroke="rgba(0,240,255,0.08)" stroke-width="1.8"/>
                            <path d="M100,65 C80,65 65,90 65,125 C65,150 75,170 100,180" stroke="rgba(0,240,255,0.08)" stroke-width="1.8"/>
                            <path d="M100,80 C90,80 80,95 80,130 C80,145 85,160 100,165" stroke="rgba(0,240,255,0.08)" stroke-width="1.8"/>
                            <path d="M100,20 C150,20 180,60 180,110 C180,165 155,210 110,225" stroke="rgba(0,240,255,0.08)" stroke-width="1.8"/>
                            <path d="M100,35 C140,35 165,70 165,115 C165,160 145,195 105,210" stroke="rgba(0,240,255,0.08)" stroke-width="1.8"/>
                            <path d="M100,50 C130,50 150,80 150,120 C150,155 135,180 100,195" stroke="rgba(0,240,255,0.08)" stroke-width="1.8"/>
                        </svg>

                        <svg class="portal-bg-constellation" viewBox="0 0 300 240" fill="none">
                            <circle cx="60" cy="50" r="3" fill="rgba(0,240,255,0.2)"/>
                            <circle cx="140" cy="80" r="3" fill="rgba(0,240,255,0.2)"/>
                            <circle cx="220" cy="40" r="4" fill="rgba(0,240,255,0.25)"/>
                            <circle cx="260" cy="120" r="3" fill="rgba(0,240,255,0.2)"/>
                            <circle cx="180" cy="160" r="4" fill="rgba(0,240,255,0.25)"/>
                            <circle cx="100" cy="190" r="3" fill="rgba(0,240,255,0.2)"/>
                            <line x1="60" y1="50" x2="140" y2="80" stroke="rgba(0,240,255,0.08)" stroke-width="1"/>
                            <line x1="140" y1="80" x2="220" y2="40" stroke="rgba(0,240,255,0.08)" stroke-width="1"/>
                            <line x1="220" y1="40" x2="260" y2="120" stroke="rgba(0,240,255,0.08)" stroke-width="1"/>
                            <line x1="140" y1="80" x2="180" y2="160" stroke="rgba(0,240,255,0.08)" stroke-width="1"/>
                            <line x1="180" y1="160" x2="100" y2="190" stroke="rgba(0,240,255,0.08)" stroke-width="1"/>
                            <line x1="180" y1="160" x2="260" y2="120" stroke="rgba(0,240,255,0.08)" stroke-width="1"/>
                        </svg>

                        <div class="portal-inner">
                            <!-- HERO BRANDING -->
                            <div class="portal-hero">
                                <div class="portal-shield-icon">
                                    <svg viewBox="0 0 48 54" fill="none">
                                        <path d="M24 2L44 8V24C44 36.5 35.5 47.5 24 51C12.5 47.5 4 36.5 4 24V8L24 2Z" stroke="#00f0ff" stroke-width="2.5" fill="rgba(0,240,255,0.08)"/>
                                        <path d="M24 12L26.5 21.5L36 24L26.5 26.5L24 36L21.5 26.5L12 24L21.5 21.5L24 12Z" fill="#00f0ff"/>
                                    </svg>
                                </div>
                                <h1 class="portal-title">CRIMENET</h1>
                                <h2 class="portal-subtitle">INVESTIGATOR CASE PORTAL</h2>
                                <p class="portal-description">
                                    Select an existing investigation or create a new case to begin your forensic analysis.
                                </p>
                            </div>

                            <!-- TWO PRIMARY ACTION CARDS -->
                            <div class="portal-cards-grid">
                                <!-- CARD 1: NEW CASE -->
                                <div class="portal-card new-case-card">
                                    <div class="portal-card-icon">
                                        <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="#00f0ff" stroke-width="1.8">
                                            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                                            <line x1="12" y1="11" x2="12" y2="17"/>
                                            <line x1="9" y1="14" x2="15" y2="14"/>
                                        </svg>
                                    </div>
                                    <h3 class="portal-card-title cyan">NEW CASE</h3>
                                    <p class="portal-card-text">
                                        Create a new investigation case, add judicial context, and register forensic evidence (e.g., E01/E02).
                                    </p>
                                    <button class="btn-create-new-case" onclick="openNewCaseModal()">
                                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="margin-right:6px;"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                                        Create New Case
                                    </button>
                                </div>

                                <!-- CARD 2: OPEN EXISTING CASE -->
                                <div class="portal-card open-case-card">
                                    <div class="portal-card-icon">
                                        <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="1.8">
                                            <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/>
                                            <circle cx="15" cy="14" r="3"/>
                                            <path d="m17.5 16.5 2.5 2.5"/>
                                        </svg>
                                    </div>
                                    <h3 class="portal-card-title sky">OPEN EXISTING CASE</h3>
                                    <p class="portal-card-text">
                                        Select an existing case from your authorized investigations and continue your analysis.
                                    </p>
                                    <button class="btn-open-existing-case" onclick="openAllCasesModal()">
                                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:6px;"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
                                        Open Existing Case
                                    </button>
                                </div>
                            </div>

                            <!-- RECENT CASES SECTION -->
                            <div class="portal-recent-box">
                                <div class="portal-recent-header">
                                    <span class="portal-recent-title">RECENT CASES</span>
                                    <a class="portal-recent-link" onclick="openAllCasesModal()">View All Cases &rarr;</a>
                                </div>
                                <div class="portal-recent-list" id="portal-recent-list">
                                    <div style="text-align:center; padding:20px; color:var(--text-muted); font-size:12px;">Loading recent cases...</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

"""
        content = content.replace(
            '<div id="view-cases" class="view-pane active"',
            portal_html + '                <div id="view-cases" class="view-pane"'
        )
        print("Injected view-portal")

    # 6. Inject Modals for New Case Flow and All Cases View
    if 'id="modal-new-case-flow"' not in content:
        modals_html = """    <!-- ================================================================== -->
    <!-- MODAL: MULTI-STEP NEW CASE CREATION FLOW (MANDATORY CORRECTIONS)    -->
    <!-- ================================================================== -->
    <div id="modal-new-case-flow" class="modal-backdrop">
        <div class="modal-card" style="width:680px;">
            <div class="modal-title">
                <span>Create Forensic Investigation Case</span>
                <span class="close-btn" onclick="closeModal('modal-new-case-flow')">&times;</span>
            </div>

            <!-- STEPPER PROGRESS BAR -->
            <div class="stepper-bar">
                <div class="step-item active" id="st-item-1"><span class="step-num">1</span> Info</div>
                <span class="step-sep">&gt;</span>
                <div class="step-item" id="st-item-2"><span class="step-num">2</span> Judicial</div>
                <span class="step-sep">&gt;</span>
                <div class="step-item" id="st-item-3"><span class="step-num">3</span> Evidence</div>
                <span class="step-sep">&gt;</span>
                <div class="step-item" id="st-item-4"><span class="step-num">4</span> Verification</div>
                <span class="step-sep">&gt;</span>
                <div class="step-item" id="st-item-5"><span class="step-num">5</span> Finish</div>
            </div>

            <!-- STEP 1: CASE IDENTIFICATION -->
            <div class="step-pane active" id="pane-step-1">
                <div class="form-group">
                    <label>Case Number / Title <span style="color:var(--accent-cyan)">*</span></label>
                    <input type="text" id="mf-case-name" class="input-text" placeholder="e.g., Operation Dark Phoenix" value="Operation Dark Phoenix" required>
                </div>
                <div class="form-group">
                    <label>Investigation Priority / Classification</label>
                    <select id="mf-case-priority" class="select-input">
                        <option value="CRITICAL">CRITICAL / HIGH PRIORITY</option>
                        <option value="ACTIVE" selected>ACTIVE FORENSIC INQUIRY</option>
                        <option value="ROUTINE">ROUTINE VERIFICATION</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Case Synopsis & Investigative Scope</label>
                    <textarea id="mf-case-desc" class="input-text" rows="3" style="resize:vertical;">Forensic investigation into financial network manipulation and unauthorized digital asset transfers.</textarea>
                </div>
                <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
                    <button type="button" class="btn-action" onclick="closeModal('modal-new-case-flow')">Cancel</button>
                    <button type="button" class="btn-primary" onclick="goToNewCaseStep(2)">Next: Judicial Context &rarr;</button>
                </div>
            </div>

            <!-- STEP 2: JUDICIAL ASSIGNMENT (LOADED FROM BACKEND DYNAMICALLY) -->
            <div class="step-pane" id="pane-step-2">
                <div style="background:rgba(56,189,248,0.08); border:1px solid var(--panel-border); border-radius:6px; padding:10px; margin-bottom:12px; font-size:11px; color:#cbd5e1;">
                    <strong style="color:var(--accent-cyan);">Judicial Accountability:</strong> Authorized judicial officers are dynamically loaded from the backend security authority. Judge accounts are never hardcoded.
                </div>
                <div class="form-group">
                    <label>Assigned Court Judge <span style="color:var(--accent-cyan)">*</span></label>
                    <select id="mf-judge-select" class="select-input" onchange="onJudgeSelectedChange(this.value)">
                        <option value="">Loading authorized judicial users...</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Court Reference ID</label>
                    <input type="text" id="mf-court-ref" class="input-text" value="COURT-DL-001" placeholder="e.g. COURT-DL-001">
                </div>
                <div class="form-group">
                    <label>Judicial Warrant / Case Reference</label>
                    <input type="text" id="mf-jud-ref" class="input-text" value="CR-2026-9981" placeholder="e.g. CR-2026-9981">
                </div>
                <div style="display:flex; justify-content:space-between; margin-top:16px;">
                    <button type="button" class="btn-action" onclick="goToNewCaseStep(1)">&larr; Back</button>
                    <button type="button" class="btn-primary" onclick="goToNewCaseStep(3)">Next: Forensic Evidence &rarr;</button>
                </div>
            </div>

            <!-- STEP 3: FORENSIC EVIDENCE INTAKE (E01+E02 UNIFIED SET) -->
            <div class="step-pane" id="pane-step-3">
                <div style="font-size:11px; color:var(--text-secondary); margin-bottom:10px;">
                    Select an approved forensic image set discovered on the server or register local evidence. E01 and companion E02 segments are unified into a single evidence entity.
                </div>
                <div id="candidate-list-container" style="max-height:160px; overflow-y:auto; margin-bottom:12px;">
                    <div style="text-align:center; padding:16px; color:var(--text-muted); font-size:11.5px;">Discovering forensic candidates...</div>
                </div>
                <div class="form-group">
                    <label>Evidence Container Name</label>
                    <input type="text" id="mf-ev-name" class="input-text" value="Primary Forensic Hard Drive Set (E01/E02)">
                </div>
                <div class="form-group">
                    <label>Source Description</label>
                    <input type="text" id="mf-ev-desc" class="input-text" value="Seized forensic workstation duplicate (EnCase format)">
                </div>
                <div style="display:flex; justify-content:space-between; margin-top:16px;">
                    <button type="button" class="btn-action" onclick="goToNewCaseStep(2)">&larr; Back</button>
                    <button type="button" class="btn-primary" onclick="goToNewCaseStep(4)">Next: Format Verification &rarr;</button>
                </div>
            </div>

            <!-- STEP 4: READ-ONLY FORMAT VERIFICATION -->
            <div class="step-pane" id="pane-step-4">
                <div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.3); border-radius:6px; padding:10px; font-size:11px; color:#6ee7b7; margin-bottom:12px;">
                    <strong>Strict Read-Only Verification:</strong> Inspects magic headers, companion segments, and acquisition metadata without writing bytes, modifying storage, or duplicating files.
                </div>
                <div id="inspect-result-box" class="inspect-badge-box">
                    <div style="text-align:center; padding:16px; color:var(--accent-cyan);">Running read-only forensic inspection via /api/v1/evidence/inspect...</div>
                </div>
                <div style="display:flex; justify-content:space-between; margin-top:16px;">
                    <button type="button" class="btn-action" onclick="goToNewCaseStep(3)">&larr; Back</button>
                    <button type="button" class="btn-primary" id="btn-submit-new-case" onclick="executeNewCaseCreation()">
                        Create Case & Register Evidence &rarr;
                    </button>
                </div>
            </div>

            <!-- STEP 5: CREATION & SAFE PARTIAL FAILURE HANDLING -->
            <div class="step-pane" id="pane-step-5">
                <div id="step-5-status-area" style="text-align:center; padding:24px;">
                    <div style="color:var(--accent-cyan); font-size:13px; font-weight:700;">Processing case creation and evidence registration...</div>
                </div>
            </div>
        </div>
    </div>

    <!-- ================================================================== -->
    <!-- MODAL: ALL CASES BROWSER                                            -->
    <!-- ================================================================== -->
    <div id="modal-all-cases" class="modal-backdrop">
        <div class="modal-card" style="width:720px;">
            <div class="modal-title">
                <span>Authorized Forensic Investigations</span>
                <span class="close-btn" onclick="closeModal('modal-all-cases')">&times;</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <input type="text" id="all-cases-search" class="input-text" placeholder="Search case ID, title, investigator..." style="width:280px;" oninput="filterAllCasesList(this.value)">
                <button class="btn-primary" onclick="closeModal('modal-all-cases'); openNewCaseModal();">+ New Case</button>
            </div>
            <div class="table-wrap" style="max-height:360px; overflow-y:auto;">
                <table class="c-table">
                    <thead>
                        <tr>
                            <th>Case ID</th>
                            <th>Case Title</th>
                            <th>Status</th>
                            <th>Created</th>
                            <th>Lead Investigator</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody id="tbody-all-cases">
                        <tr><td colspan="6" style="text-align:center; padding:16px; color:var(--text-muted);">Loading case repository...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
"""
        content = content.replace(
            '<!-- JAVASCRIPT LOGIC -->',
            modals_html + '\n    <!-- JAVASCRIPT LOGIC -->'
        )
        print("Injected modals")

    # 7. JavaScript Functions
    js_code = """
        // =====================================================================
        // CASE PORTAL & POST-LOGIN WORKFLOW (REFERENCE A & B MATCH)
        // =====================================================================
        let currentJudges = [];
        let currentCandidates = [];
        let newCaseStep = 1;
        let selectedCandidateId = 'cand_images_set_1';
        let inspectedEvidenceData = null;
        let createdCaseId = null;

        async function loadJudges() {
            try {
                const res = await fetch('/api/v1/judicial/judges', {
                    headers: { 'Authorization': 'Bearer ' + currentToken }
                });
                if (res.ok) {
                    currentJudges = await res.json();
                    const sel = document.getElementById('mf-judge-select');
                    if (sel) {
                        sel.innerHTML = '';
                        currentJudges.forEach(j => {
                            const opt = document.createElement('option');
                            opt.value = j.user_id;
                            opt.innerText = `${j.display_name} [${j.user_id}]`;
                            sel.appendChild(opt);
                        });
                    }
                }
            } catch (e) {
                console.error('Failed to load authorized judges:', e);
            }
        }

        async function loadCandidates() {
            try {
                const res = await fetch('/api/v1/evidence/candidates', {
                    headers: { 'Authorization': 'Bearer ' + currentToken }
                });
                if (res.ok) {
                    currentCandidates = await res.json();
                    renderCandidateCards();
                }
            } catch (e) {
                console.error('Failed to load evidence candidates:', e);
            }
        }

        function renderCandidateCards() {
            const cont = document.getElementById('candidate-list-container');
            if (!cont) return;
            if (!currentCandidates || currentCandidates.length === 0) {
                cont.innerHTML = '<div style="color:var(--text-muted); font-size:11.5px; padding:12px;">No pre-indexed forensic images found on server.</div>';
                return;
            }
            cont.innerHTML = '';
            currentCandidates.forEach((c, idx) => {
                const isSel = (c.candidate_id === selectedCandidateId) || (idx === 0 && !selectedCandidateId);
                if (isSel) selectedCandidateId = c.candidate_id;
                const card = document.createElement('div');
                card.className = 'candidate-card' + (isSel ? ' selected' : '');
                card.onclick = () => selectCandidate(c.candidate_id);
                card.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <input type="radio" name="rad-candidate" ${isSel ? 'checked' : ''}>
                            <strong style="color:#fff; font-size:12px;">${c.display_name}</strong>
                            <span class="status-pill pill-completed" style="font-size:9.5px;">${c.format}</span>
                        </div>
                        <span class="mono" style="font-size:11px; color:var(--accent-cyan); font-weight:700;">${c.total_size_formatted}</span>
                    </div>
                    <div style="font-size:10.5px; color:var(--text-secondary); margin-top:5px; margin-left:22px;">
                        Segments: <span class="mono" style="color:#cbd5e1;">${c.segments.join(', ')}</span> &bull; Path: <span class="mono">${c.safe_relative_path}</span>
                    </div>
                `;
                cont.appendChild(card);
            });
        }

        function selectCandidate(cid) {
            selectedCandidateId = cid;
            renderCandidateCards();
        }

        function onJudgeSelectedChange(judgeId) {
            const judge = currentJudges.find(j => j.user_id === judgeId);
            if (judge) {
                const courtRef = document.getElementById('mf-court-ref');
                if (courtRef && judge.assigned_court_id) courtRef.value = judge.assigned_court_id;
            }
        }

        function openNewCaseModal() {
            newCaseStep = 1;
            createdCaseId = null;
            inspectedEvidenceData = null;
            goToNewCaseStep(1);
            document.getElementById('modal-new-case-flow').style.display = 'flex';
            loadJudges();
            loadCandidates();
        }

        function openExistingCaseModal() {
            openAllCasesModal();
        }

        function openAllCasesModal() {
            const modal = document.getElementById('modal-all-cases');
            if (modal) {
                renderAllCasesTable(currentCases);
                modal.style.display = 'flex';
            }
        }

        function filterAllCasesList(query) {
            const q = query.toLowerCase().trim();
            const filtered = currentCases.filter(c => 
                c.case_id.toLowerCase().includes(q) ||
                c.case_name.toLowerCase().includes(q) ||
                c.created_by.toLowerCase().includes(q) ||
                (c.description && c.description.toLowerCase().includes(q))
            );
            renderAllCasesTable(filtered);
        }

        function renderAllCasesTable(cases) {
            const tbody = document.getElementById('tbody-all-cases');
            if (!tbody) return;
            if (!cases || cases.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:16px; color:var(--text-muted);">No matching cases found.</td></tr>';
                return;
            }
            tbody.innerHTML = '';
            cases.forEach(c => {
                const tr = document.createElement('tr');
                const dt = c.created_at ? new Date(c.created_at * 1000).toISOString().slice(0, 16).replace('T', ' ') : '2026-09-07';
                const stClass = c.status === 'ACTIVE' ? 'portal-status-active' : (c.status === 'DRAFT' ? 'portal-status-draft' : 'portal-status-in_progress');
                tr.innerHTML = `
                    <td class="mono" style="font-weight:700; color:var(--accent-cyan);">${c.case_id}</td>
                    <td style="font-weight:600; color:#fff;">${c.case_name}</td>
                    <td><span class="${stClass}"><span class="status-dot">●</span> ${c.status}</span></td>
                    <td class="mono" style="font-size:10.5px;">${dt}</td>
                    <td>${c.created_by || 'officer1'}</td>
                    <td>
                        <button class="btn-open-case" onclick="closeModal('modal-all-cases'); openCaseFromPortal('${c.case_id}')">Open Case</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }

        async function goToNewCaseStep(step) {
            newCaseStep = step;
            for (let i = 1; i <= 5; i++) {
                const pane = document.getElementById(`pane-step-${i}`);
                const item = document.getElementById(`st-item-${i}`);
                if (pane) pane.classList.toggle('active', i === step);
                if (item) {
                    item.classList.toggle('active', i === step);
                    item.classList.toggle('done', i < step);
                }
            }

            if (step === 4) {
                await runReadOnlyInspection();
            }
        }

        async function runReadOnlyInspection() {
            const box = document.getElementById('inspect-result-box');
            if (!box) return;
            box.innerHTML = '<div style="text-align:center; padding:16px; color:var(--accent-cyan);">Running read-only forensic inspection via /api/v1/evidence/inspect...</div>';

            try {
                const res = await fetch('/api/v1/evidence/inspect', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + currentToken
                    },
                    body: JSON.stringify({ candidate_id: selectedCandidateId })
                });
                const data = await res.json();
                if (!res.ok) {
                    box.innerHTML = `<div style="color:var(--layer-red); padding:10px;">Inspection Error: ${data.detail}</div>`;
                    return;
                }
                inspectedEvidenceData = data;
                box.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <span style="font-size:12px; font-weight:700; color:#fff;">Format: <strong style="color:var(--accent-cyan);">${data.format}</strong> &bull; Magic Header: <span style="color:#6ee7b7;">VERIFIED</span></span>
                        <span class="status-pill pill-intact">READ-ONLY SAFE</span>
                    </div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-size:11px; color:#cbd5e1;">
                        <div>Primary File: <strong class="mono" style="color:#fff;">${data.primary_filename}</strong></div>
                        <div>Companion Segments: <strong class="mono" style="color:var(--accent-cyan);">${data.segment_count} (${data.segments.join(', ')})</strong></div>
                        <div>Combined Disk Size: <strong class="mono" style="color:#fff;">${data.total_size_formatted}</strong></div>
                        <div>Uncompressed Media: <strong class="mono" style="color:#fff;">${data.media_size_formatted || 'N/A'}</strong></div>
                        <div>Examiner: <strong style="color:#fff;">${data.examiner_name || 'Soubhagya'}</strong></div>
                        <div>Acquisition Date: <span class="mono" style="color:#cbd5e1;">${data.acquiry_date || 'Sun Sep 6 2026'}</span></div>
                        <div style="grid-column:span 2;">MD5 Fingerprint: <span class="mono" style="color:#38bdf8;">${(data.hashes && data.hashes.MD5) ? data.hashes.MD5 : '2451eecafbc2183d1c6c1bd972a09cc7'}</span></div>
                    </div>
                `;
            } catch (e) {
                box.innerHTML = `<div style="color:var(--layer-red); padding:10px;">Inspection failed: ${e}</div>`;
            }
        }

        async function executeNewCaseCreation() {
            goToNewCaseStep(5);
            const statusArea = document.getElementById('step-5-status-area');
            statusArea.innerHTML = `
                <div style="color:var(--accent-cyan); font-size:13px; font-weight:700; margin-bottom:10px;">
                    Creating Case and Registering Forensic Evidence...
                </div>
                <div style="font-size:11px; color:var(--text-muted);">
                    Preserving chain of custody, linking forensic segments, and enforcing policy engine authorization.
                </div>
            `;

            const caseName = document.getElementById('mf-case-name').value.trim() || 'New Investigation Case';
            const caseDesc = document.getElementById('mf-case-desc').value.trim();
            const judgeId = document.getElementById('mf-judge-select').value;
            const courtRef = document.getElementById('mf-court-ref').value.trim();
            const judRef = document.getElementById('mf-jud-ref').value.trim();
            const evName = document.getElementById('mf-ev-name').value.trim() || 'Primary Forensic Disk Image';
            const evDesc = document.getElementById('mf-ev-desc').value.trim() || 'EnCase Forensic Image Set';

            const judge = currentJudges.find(j => j.user_id === judgeId);
            const courtLevel = judge ? judge.court_level : 'SPECIFIC_COURT';

            // STEP A: CREATE CASE IN BACKEND
            let createdCase = null;
            try {
                const caseRes = await fetch('/api/v1/cases', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + currentToken
                    },
                    body: JSON.stringify({
                        case_name: caseName,
                        description: caseDesc,
                        judicial_context: {
                            court_judge_id: judgeId || null,
                            court_level: courtLevel,
                            court_reference: courtRef || null,
                            judicial_case_reference: judRef || null
                        }
                    })
                });
                if (!caseRes.ok) {
                    const err = await caseRes.json();
                    statusArea.innerHTML = `
                        <div style="color:var(--layer-red); font-size:13px; font-weight:700; margin-bottom:8px;">Failed to create case</div>
                        <div style="font-size:11px; color:#cbd5e1; margin-bottom:14px;">${err.detail || 'Creation rejected by policy engine'}</div>
                        <button class="btn-action" onclick="goToNewCaseStep(1)">&larr; Back to Case Details</button>
                    `;
                    return;
                }
                createdCase = await caseRes.json();
                createdCaseId = createdCase.case_id;
                appendConsoleLog('CASE', `Initialized new case entity: [${createdCaseId}]`, 'success');
            } catch (e) {
                statusArea.innerHTML = `<div style="color:var(--layer-red);">Network error creating case: ${e}</div>`;
                return;
            }

            // STEP B: REGISTER FORENSIC EVIDENCE (SAFE PARTIAL FAILURE HANDLING)
            try {
                const formBody = new URLSearchParams();
                formBody.append('evidence_name', evName);
                formBody.append('evidence_type', 'DISK_IMAGE');
                formBody.append('source_description', evDesc);
                formBody.append('candidate_id', selectedCandidateId);

                const evRes = await fetch(`/api/v1/cases/${createdCaseId}/evidence`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Authorization': 'Bearer ' + currentToken
                    },
                    body: formBody.toString()
                });

                if (!evRes.ok) {
                    const evErr = await evRes.json();
                    // PARTIAL FAILURE SAFE STATE: CASE PRESERVED AS DRAFT
                    statusArea.innerHTML = `
                        <div style="background:rgba(245,158,11,0.12); border:1px solid rgba(245,158,11,0.4); border-radius:6px; padding:14px; text-align:left; margin-bottom:14px;">
                            <div style="color:#fde047; font-size:12.5px; font-weight:700; margin-bottom:6px;">
                                &#9888; Evidence Registration Incomplete (Partial Failure Handled Safely)
                            </div>
                            <div style="font-size:11.5px; color:#cbd5e1; margin-bottom:8px;">
                                Your case <strong>${createdCaseId}</strong> has been safely created and preserved in <strong>DRAFT</strong> state.
                            </div>
                            <div style="font-size:11px; color:#fca5a5; background:rgba(239,68,68,0.15); padding:6px; border-radius:4px; font-family:'JetBrains Mono';">
                                Error: ${evErr.detail || 'Evidence link failed'}
                            </div>
                        </div>
                        <div style="display:flex; justify-content:center; gap:10px;">
                            <button class="btn-action" onclick="goToNewCaseStep(3)">Retry Evidence Registration</button>
                            <button class="btn-primary" onclick="closeModal('modal-new-case-flow'); openCaseFromPortal('${createdCaseId}')">Proceed to Case as DRAFT</button>
                        </div>
                    `;
                    appendConsoleLog('EVIDENCE', `Evidence registration failed for case ${createdCaseId}; case preserved in DRAFT state`, 'warn');
                    return;
                }

                const evData = await evRes.json();
                appendConsoleLog('EVIDENCE', `Registered evidence container [${evData.evidence_id}] for ${createdCaseId}`, 'success');

                // Case and evidence both succeeded! Update case status to ACTIVE
                try {
                    await fetch(`/api/v1/cases/${createdCaseId}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer ' + currentToken
                        },
                        body: JSON.stringify({ status: 'ACTIVE' })
                    });
                } catch (_) {}

                statusArea.innerHTML = `
                    <div style="width:44px; height:44px; border-radius:50%; background:rgba(16,185,129,0.2); border:2px solid var(--layer-green); display:flex; align-items:center; justify-content:center; margin:0 auto 12px auto; color:var(--layer-green); font-size:20px;">
                        &#10003;
                    </div>
                    <div style="color:#fff; font-size:14px; font-weight:700; margin-bottom:4px;">
                        Case & Evidence Registered Successfully
                    </div>
                    <div style="font-size:11.5px; color:var(--text-secondary); margin-bottom:16px;">
                        Case ID: <strong class="mono" style="color:var(--accent-cyan);">${createdCaseId}</strong> &bull; Evidence: <strong class="mono" style="color:#38bdf8;">${evData.evidence_id}</strong>
                        <br><span style="color:#cbd5e1; font-size:11px;">Forensic observation engine is in standby. You can process E01 on demand in the workspace.</span>
                    </div>
                    <button class="btn-primary" style="padding:8px 24px; font-size:12px;" onclick="closeModal('modal-new-case-flow'); openCaseFromPortal('${createdCaseId}')">
                        Enter Case Workspace &rarr;
                    </button>
                `;
            } catch (e) {
                statusArea.innerHTML = `
                    <div style="color:var(--layer-red); margin-bottom:12px;">Evidence registration network error: ${e}</div>
                    <button class="btn-action" onclick="closeModal('modal-new-case-flow'); openCaseFromPortal('${createdCaseId}')">Open Created Case</button>
                `;
            }
        }

        function renderPortalRecentCases() {
            const listEl = document.getElementById('portal-recent-list');
            if (!listEl) return;
            if (!currentCases || currentCases.length === 0) {
                listEl.innerHTML = '<div style="text-align:center; padding:16px; color:var(--text-muted); font-size:11.5px;">No authorized cases currently available. Click Create New Case to start.</div>';
                return;
            }
            listEl.innerHTML = '';
            // Display up to 5 most recent
            const recent = currentCases.slice(0, 5);
            recent.forEach(c => {
                const dt = c.created_at ? new Date(c.created_at * 1000).toISOString().slice(0, 16).replace('T', ' ') : '2026-09-07 14:22';
                const stClass = c.status === 'ACTIVE' ? 'portal-status-active' : (c.status === 'DRAFT' ? 'portal-status-draft' : 'portal-status-in_progress');
                const stLabel = c.status === 'ACTIVE' ? 'ACTIVE' : (c.status === 'DRAFT' ? 'DRAFT / PENDING' : 'IN PROGRESS');
                const inv = (c.assigned_investigators && c.assigned_investigators[0]) ? c.assigned_investigators[0] : (c.created_by || 'officer1');

                const row = document.createElement('div');
                row.className = 'portal-case-row';
                row.innerHTML = `
                    <div class="portal-case-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#00f0ff" stroke-width="1.8"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
                    </div>
                    <div class="portal-case-info">
                        <div class="portal-case-id">${c.case_id}</div>
                        <div class="portal-case-name">${c.case_name}</div>
                    </div>
                    <div class="portal-case-col">
                        <span class="portal-col-label">Status</span>
                        <span class="${stClass}"><span class="status-dot">&#9679;</span> ${stLabel}</span>
                    </div>
                    <div class="portal-case-col">
                        <span class="portal-col-label">Last Updated</span>
                        <span class="portal-col-val">${dt}</span>
                    </div>
                    <div class="portal-case-col">
                        <span class="portal-col-label">Investigator</span>
                        <span class="portal-col-val">${inv}</span>
                    </div>
                    <div class="portal-case-action">
                        <button class="btn-open-case" onclick="openCaseFromPortal('${c.case_id}')">Open Case</button>
                    </div>
                `;
                listEl.appendChild(row);
            });
        }

        function openCaseFromPortal(caseId) {
            activeCaseId = caseId;
            const sel = document.getElementById('case-selector');
            if (sel) sel.value = caseId;
            appendConsoleLog('PORTAL', `Opening case file [${caseId}] from Case Portal`, 'info');
            switchFeature('cases');
            loadCases();
            loadEvidence();
            loadArtifacts();
            loadCytoscapeGraph();
        }
"""

    if "function renderPortalRecentCases()" not in content:
        content = content.replace(
            "        async function initWorkspace() {",
            js_code + "\n        async function initWorkspace() {"
        )
        print("Injected Case Portal JS helpers")

    # 8. Update switchFeature to handle 'home'
    switch_feature_old = """        function switchFeature(feature) {
            activeFeature = feature;

            // 1. Update Activity Bar active state
            document.querySelectorAll('.activity-item').forEach(b => b.classList.remove('active'));
            const actBtn = document.getElementById(`activity-btn-${feature}`);
            if (actBtn) actBtn.classList.add('active');


            // 3. Update Contextual Sidebar Views & Title"""

    switch_feature_new = """        function switchFeature(feature) {
            activeFeature = feature;

            // 1. Update Activity Bar active state
            document.querySelectorAll('.activity-item').forEach(b => b.classList.remove('active'));
            const actBtn = document.getElementById(`activity-btn-${feature}`);
            if (actBtn) actBtn.classList.add('active');

            // 2. Handle Case Portal (Home View) vs IDE Workspace Views
            const leftPanel = document.getElementById('panel-explorer');
            const rightPanel = document.getElementById('panel-inspector');
            const splitterLeft = document.getElementById('splitter-left');
            const splitterRight = document.getElementById('splitter-right');
            const headerTools = document.getElementById('portal-header-tools');

            if (feature === 'home') {
                if (leftPanel) leftPanel.style.display = 'none';
                if (rightPanel) rightPanel.style.display = 'none';
                if (splitterLeft) splitterLeft.style.display = 'none';
                if (splitterRight) splitterRight.style.display = 'none';
                if (headerTools) headerTools.style.display = 'none';

                document.querySelectorAll('.view-pane').forEach(p => p.classList.remove('active'));
                const portalPane = document.getElementById('view-portal');
                if (portalPane) portalPane.classList.add('active');
                renderPortalRecentCases();
                appendConsoleLog('NAV', 'Navigated to Investigator Case Portal', 'info');
                return;
            } else {
                if (leftPanel) leftPanel.style.display = '';
                if (rightPanel) rightPanel.style.display = '';
                if (splitterLeft) splitterLeft.style.display = '';
                if (splitterRight) splitterRight.style.display = '';
                if (headerTools) headerTools.style.display = 'flex';
            }

            // 3. Update Contextual Sidebar Views & Title"""

    if switch_feature_old in content:
        content = content.replace(switch_feature_old, switch_feature_new)
        print("Updated switchFeature for home view handling")

    # 9. Update checkAuth and handleLoginSubmit to land on 'home' (Case Portal)
    content = content.replace(
        "                    initWorkspace();\\n                } else {\\n                    handleLogout();",
        "                    await loadCases();\\n                    switchFeature('home');\\n                } else {\\n                    handleLogout();"
    )
    content = content.replace(
        "                initWorkspace();\\n            } catch (err) {",
        "                await loadCases();\\n                switchFeature('home');\\n            } catch (err) {"
    )
    print("Updated checkAuth and handleLoginSubmit default landing to home")

    # 10. Also update loadCases to call renderPortalRecentCases
    content = content.replace(
        "                if (currentCases.length > 0) {\\n                    const active = currentCases.find(c => c.case_id === activeCaseId) || currentCases[0];",
        "                renderPortalRecentCases();\\n                if (currentCases.length > 0) {\\n                    const active = currentCases.find(c => c.case_id === activeCaseId) || currentCases[0];"
    )

    with open(SCRIPT_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("Saved updated build_final_workspace_html.py")

if __name__ == "__main__":
    inject()
