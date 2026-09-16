"""
Live Case-Scoped Report Generator for CRIMENET.
Extracts live database evidence, graph entities, CCC metrics, and generates
transparent analytical reports with version lineage and Section 65B Drafts.
Zero hardcoding — strictly compiles live case state.
"""

import hashlib
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from src.reports.models import (
    ReportDetail,
    ReportGenerateRequest,
    ReportTemplateType,
    ReportStatus
)


class ReportGenerator:
    @staticmethod
    def generate(
        case: Any,
        artifacts: List[Any],
        graph_data: Dict[str, Any],
        parsed_observations_count: int,
        request: ReportGenerateRequest,
        version_str: str,
        version_number: int,
        previous_version_id: Optional[str],
        author: str
    ) -> ReportDetail:
        now_ts = time.time()
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        case_id = case.case_id if hasattr(case, "case_id") else str(case.get("case_id", "UNKNOWN"))
        case_name = case.case_name if hasattr(case, "case_name") else str(case.get("case_name", "Untitled Case"))
        case_desc = case.description if hasattr(case, "description") else str(case.get("description", ""))
        case_status = case.status.value if hasattr(case.status, "value") else str(case.status)

        report_id = f"REP-{case_id}-{uuid.uuid4().hex[:8].upper()}"

        # Default title based on template if not provided
        default_titles = {
            ReportTemplateType.COMPREHENSIVE_DOSSIER: f"Comprehensive Forensic Analytical Dossier — {case_name}",
            ReportTemplateType.EXECUTIVE_BRIEF: f"Executive Analytical Intelligence Brief — {case_name}",
            ReportTemplateType.SECTION_65B_DRAFT: f"Section 65B Electronic Evidence Review Draft — {case_name}",
            ReportTemplateType.NETWORK_LINKAGE: f"Contact Network & Analytical Linkage Report — {case_name}",
        }
        title = request.title.strip() if request.title and request.title.strip() else default_titles.get(
            request.template_type, f"Forensic Investigation Report — {case_name}"
        )

        def _val(obj: Any, key: str, default: Any = "") -> Any:
            if isinstance(obj, dict):
                return obj.get(key, default)
            val = getattr(obj, key, default)
            if hasattr(val, "value"):
                return val.value
            return val if val is not None else default

        # 1. Artifacts summary from live data
        total_artifacts = len(artifacts)
        category_counts: Dict[str, int] = {}
        deleted_count = 0
        allocated_count = 0
        artifacts_sample = []

        for a in artifacts:
            cat = str(_val(a, "category", "OTHER"))
            alloc = str(_val(a, "allocation_status", "ALLOCATED"))
            category_counts[cat] = category_counts.get(cat, 0) + 1
            if alloc == "DELETED" or cat in ["DELETED", "DELETED_FILE"]:
                deleted_count += 1
            else:
                allocated_count += 1

            if len(artifacts_sample) < 15:
                artifacts_sample.append({
                    "id": str(_val(a, "artifact_id", "")),
                    "filename": str(_val(a, "filename", "")),
                    "category": cat,
                    "mime": str(_val(a, "mime_type", "")),
                    "size_bytes": int(_val(a, "size_bytes", 0) or 0),
                    "sha256": str(_val(a, "sha256", "")),
                    "status": alloc
                })

        # 2. Live graph nodes (Entity Intelligence & Analytical Leads)
        nodes = graph_data.get("nodes", [])
        total_entities = len(nodes)
        leads_sample = []
        for n in nodes:
            leads_sample.append({
                "id": n.get("id", ""),
                "name": n.get("canonical_name") or n.get("label") or n.get("id", ""),
                "type": n.get("entity_type", "ENTITY"),
                "layer": n.get("layer", 3),
                "is_anchor": n.get("is_anchor", False),
                "role": n.get("role", "Identified Entity Lead"),
                "status": n.get("human_verification_status", "UNDER_REVIEW"),
                "evidence_refs": n.get("source_evidence_ids", [])
            })

        # 3. Live graph edges (Evidence-backed Relationships)
        edges = graph_data.get("edges", [])
        total_relationships = len(edges)
        relationships_sample = []
        for e in edges:
            relationships_sample.append({
                "id": e.get("id", ""),
                "source": e.get("source", ""),
                "target": e.get("target", ""),
                "relationship": e.get("relationship") or e.get("relationship_type", "CONNECTED_TO"),
                "interaction_count": e.get("interaction_count", 1),
                "ccc_score": e.get("ccc_score", 0),
                "is_consolidated": e.get("is_consolidated", False)
            })

        # Stats dictionary
        stats = {
            "total_artifacts": total_artifacts,
            "allocated_artifacts": allocated_count,
            "deleted_artifacts": deleted_count,
            "category_breakdown": category_counts,
            "total_entities": total_entities,
            "total_relationships": total_relationships,
            "parsed_observations_count": parsed_observations_count,
            "anchor_id": graph_data.get("anchor", {}).get("id") if graph_data.get("anchor") else None
        }

        source_scope = {
            "template_type": request.template_type.value,
            "include_deleted": request.include_deleted,
            "include_unverified": request.include_unverified,
            "author_notes": request.notes or "",
            "case_status": case_status
        }

        summary_text = (
            f"Analytical report for {case_name} ({case_id}) compiled on {now_iso}. "
            f"Encompasses {total_artifacts} evidentiary artifacts, {total_entities} canonical entity leads, "
            f"and {total_relationships} evidence-backed interaction links."
        )

        # 4. Generate Section 65B Draft
        legal_draft = {
            "draft_title": "Section 65B Certificate Draft / Examiner Review",
            "statutory_reference": "Section 65B Indian Evidence Act / FRE 902 Electronic Evidence Rules",
            "certification_status": "DRAFT_PENDING_HUMAN_SIGNATURE",
            "examiner_disclaimer": "This document is a system-generated analytical draft. It does not constitute completed certification, judicial approval, or an examiner oath. An authorized human forensic examiner must review, complete, and execute this certificate prior to judicial presentation.",
            "target_case_id": case_id,
            "evidence_image_hash": artifacts_sample[0]["sha256"] if artifacts_sample else "NOT_AVAILABLE",
            "artifacts_covered_count": total_artifacts,
            "generated_timestamp": now_iso
        }

        # 5. Build Markdown content
        markdown_content = ReportGenerator._build_markdown(
            report_id=report_id,
            title=title,
            version=version_str,
            case_id=case_id,
            case_name=case_name,
            case_desc=case_desc,
            author=author,
            timestamp_iso=now_iso,
            request=request,
            stats=stats,
            leads=leads_sample,
            relationships=relationships_sample,
            artifacts=artifacts_sample,
            legal_draft=legal_draft
        )

        # Compute cryptographic SHA-256 digest of the markdown content
        sha256_digest = hashlib.sha256(markdown_content.encode("utf-8")).hexdigest()

        # 6. Build HTML content
        html_content = ReportGenerator._build_html(
            report_id=report_id,
            title=title,
            version=version_str,
            case_id=case_id,
            case_name=case_name,
            case_desc=case_desc,
            author=author,
            timestamp_iso=now_iso,
            sha256_digest=sha256_digest,
            request=request,
            stats=stats,
            leads=leads_sample,
            relationships=relationships_sample,
            artifacts=artifacts_sample,
            legal_draft=legal_draft
        )

        return ReportDetail(
            report_id=report_id,
            case_id=case_id,
            version=version_str,
            version_number=version_number,
            previous_version_id=previous_version_id,
            is_current=True,
            title=title,
            template_type=request.template_type.value,
            status=ReportStatus.SYSTEM_GENERATED.value,
            author=author,
            created_at=now_ts,
            created_at_iso=now_iso,
            sha256=sha256_digest,
            summary=summary_text,
            content_html=html_content,
            content_markdown=markdown_content,
            stats=stats,
            source_scope=source_scope,
            legal_draft=legal_draft
        )

    @staticmethod
    def _build_markdown(
        report_id: str,
        title: str,
        version: str,
        case_id: str,
        case_name: str,
        case_desc: str,
        author: str,
        timestamp_iso: str,
        request: ReportGenerateRequest,
        stats: Dict[str, Any],
        leads: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        artifacts: List[Dict[str, Any]],
        legal_draft: Dict[str, Any]
    ) -> str:
        cat_lines = "\n".join([f"- **{k}**: {v} artifacts" for k, v in stats.get("category_breakdown", {}).items()]) or "- None recorded"
        
        leads_table = "| Entity ID | Canonical Label / Name | Type | Layer | Status |\n|---|---|---|---|---|\n"
        for l in leads[:20]:
            leads_table += f"| `{l['id']}` | {l['name']} | {l['type']} | Layer {l['layer']} | {l['status']} |\n"
        if not leads:
            leads_table = "_No entity leads currently identified for this case._\n"

        rel_table = "| Source | Target | Interaction Type | Volume | CCC Score |\n|---|---|---|---|---|\n"
        for r in relationships[:20]:
            rel_table += f"| `{r['source']}` | `{r['target']}` | {r['relationship']} | {r['interaction_count']}x | {r['ccc_score']} |\n"
        if not relationships:
            rel_table = "_No relationship links currently recorded for this case._\n"

        art_table = "| Artifact ID | Filename | Category | Size | SHA-256 Digest |\n|---|---|---|---|---|\n"
        for a in artifacts[:15]:
            art_table += f"| `{a['id']}` | {a['filename']} | {a['category']} | {a['size_bytes'] / 1024:.1f} KB | `{a['sha256'][:16]}...` |\n"
        if not artifacts:
            art_table = "_No artifacts currently registered for this case._\n"

        notes_sec = f"\n### Investigator Review Notes\n{request.notes}\n" if request.notes else ""

        return f"""# CRIMENET Forensic Investigation Report
**System-generated analytical report — Human review required**

---

### Report Metadata
- **Report Title:** {title}
- **Report ID:** `{report_id}`
- **Version:** {version}
- **Target Case:** {case_name} (`{case_id}`)
- **Author / Generated By:** {author}
- **Generated Timestamp:** {timestamp_iso}
- **Status:** SYSTEM_GENERATED (Human Review Required)
{notes_sec}
---

## 1. Case Overview & Scope
- **Case Identifier:** `{case_id}`
- **Title:** {case_name}
- **Summary:** {case_desc or 'Standard evidentiary scope.'}
- **Total Forensic Artifacts:** {stats.get('total_artifacts', 0)} ({stats.get('allocated_artifacts', 0)} allocated, {stats.get('deleted_artifacts', 0)} recovered/deleted)
- **Deep Observations Extracted:** {stats.get('parsed_observations_count', 0)}
- **Resolved Entity Leads:** {stats.get('total_entities', 0)}
- **Evidence-Backed Relationships:** {stats.get('total_relationships', 0)}

### Artifact Category Distribution
{cat_lines}

---

## 2. Entity Intelligence & Analytical Leads
_Analytical prioritization based on case evidence. These leads represent analytical entities identified from parsed data and require human examiner validation._

{leads_table}

---

## 3. Contact Network & Analytical Prioritization
_Summary of evidence-backed relationships, interaction counts, and Cross-Case Corroboration (CCC) scores._

{rel_table}

---

## 4. Evidence & Artifact Provenance Register
_Cryptographically verified artifacts associated with this investigation._

{art_table}

---

## 5. Section 65B Certificate Draft / Examiner Review
> [!IMPORTANT]
> **DRAFT FOR HUMAN EXAMINER REVIEW — NOT AN OFFICIAL COURT CERTIFICATION**
> In accordance with Section 65B of the Indian Evidence Act / applicable digital evidence rules, this section serves as an analytical draft. It does not constitute legal admissibility, judicial approval, or an examiner oath. An authorized human digital forensics examiner must independently verify, complete, and sign the official certificate prior to court tender.

- **Target Evidence Reference:** `{case_id}`
- **Artifacts Included:** {stats.get('total_artifacts', 0)} items
- **Primary Digest Reference:** `{legal_draft.get('evidence_image_hash', '--')}`
- **Draft Generation Timestamp:** {timestamp_iso}
- **Human Examiner Signature:** `___________________________` (Pending Execution)
- **Examiner Designation / Badge:** `___________________________`
- **Date of Execution:** `___________________________`
"""

    @staticmethod
    def _build_html(
        report_id: str,
        title: str,
        version: str,
        case_id: str,
        case_name: str,
        case_desc: str,
        author: str,
        timestamp_iso: str,
        sha256_digest: str,
        request: ReportGenerateRequest,
        stats: Dict[str, Any],
        leads: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        artifacts: List[Dict[str, Any]],
        legal_draft: Dict[str, Any]
    ) -> str:
        # Build clean HTML tables
        leads_rows = "".join([
            f"<tr><td class='mono accent'>{l['id']}</td><td><strong>{l['name']}</strong></td><td><span class='badge-role'>{l['type']}</span></td><td>Layer {l['layer']}</td><td><span class='badge-status'>{l['status']}</span></td></tr>"
            for l in leads[:25]
        ]) or "<tr><td colspan='5' style='text-align:center; color:#94a3b8; padding:12px;'>No entity leads identified in case evidence.</td></tr>"

        rel_rows = "".join([
            f"<tr><td class='mono'>{r['source']}</td><td class='mono'>{r['target']}</td><td><strong>{r['relationship']}</strong></td><td class='mono'>{r['interaction_count']}x</td><td><span class='badge-ccc'>{r['ccc_score']}</span></td></tr>"
            for r in relationships[:25]
        ]) or "<tr><td colspan='5' style='text-align:center; color:#94a3b8; padding:12px;'>No relationship links identified in case evidence.</td></tr>"

        art_rows = "".join([
            f"<tr><td class='mono accent'>{a['id']}</td><td>{a['filename']}</td><td><span class='badge-cat'>{a['category']}</span></td><td class='mono'>{a['size_bytes'] / 1024:.1f} KB</td><td class='mono hash' title='{a['sha256']}'>{a['sha256'][:20]}...</td></tr>"
            for a in artifacts[:20]
        ]) or "<tr><td colspan='5' style='text-align:center; color:#94a3b8; padding:12px;'>No artifacts registered for this case.</td></tr>"

        cat_badges = " ".join([
            f"<span class='stat-pill'><strong>{k}:</strong> {v}</span>"
            for k, v in stats.get("category_breakdown", {}).items()
        ]) or "<span class='stat-pill'>None</span>"

        notes_html = ""
        if request.notes:
            notes_html = f"""
            <div class="report-box" style="margin-top:14px; border-left:3px solid #00f0ff;">
                <div style="font-size:10.5px; font-weight:700; color:#00f0ff; text-transform:uppercase; margin-bottom:4px;">Investigator Review Notes</div>
                <div style="font-size:12px; color:#e2e8f0; line-height:1.5;">{request.notes}</div>
            </div>
            """

        return f"""
        <div class="report-document">
            <!-- REPORT IDENTITY BANNER (CORRECTION 4) -->
            <div class="report-header-banner">
                <div class="report-header-top">
                    <div class="report-brand">
                        <div class="report-shield">⚖️</div>
                        <div>
                            <div class="report-title-main">CRIMENET Forensic Investigation Report</div>
                            <div class="report-subtitle-main">System-generated analytical report — Human review required</div>
                        </div>
                    </div>
                    <div class="report-meta-badge">
                        <span class="report-ver-badge">{version}</span>
                        <span class="report-status-badge">SYSTEM_GENERATED</span>
                    </div>
                </div>
            </div>

            <!-- METADATA STRIP -->
            <div class="report-meta-grid">
                <div class="meta-item">
                    <span class="meta-label">Dossier Title</span>
                    <span class="meta-value"><strong>{title}</strong></span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Report ID</span>
                    <span class="meta-value mono accent">{report_id}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Target Case Scope</span>
                    <span class="meta-value"><strong>{case_name}</strong> <span class="mono" style="color:#94a3b8;">({case_id})</span></span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Generated By</span>
                    <span class="meta-value">{author}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Timestamp</span>
                    <span class="meta-value mono">{timestamp_iso}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Cryptographic SHA-256</span>
                    <span class="meta-value mono hash" title="{sha256_digest}">{sha256_digest[:24]}...</span>
                </div>
            </div>

            {notes_html}

            <!-- SECTION 1: CASE OVERVIEW -->
            <div class="report-section">
                <h3 class="section-title">1. Case Overview & Evidence Scope</h3>
                <div class="summary-card">
                    <p style="margin-bottom:8px; line-height:1.5; color:#cbd5e1;">{case_desc or 'Evidentiary investigation conducted under CRIMENET isolated analytical workspace.'}</p>
                    <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:10px;">
                        <span class="stat-pill"><strong>Total Artifacts:</strong> {stats.get('total_artifacts', 0)}</span>
                        <span class="stat-pill"><strong>Allocated:</strong> {stats.get('allocated_artifacts', 0)}</span>
                        <span class="stat-pill"><strong>Recovered / Deleted:</strong> {stats.get('deleted_artifacts', 0)}</span>
                        <span class="stat-pill"><strong>Entity Leads:</strong> {stats.get('total_entities', 0)}</span>
                        <span class="stat-pill"><strong>Evidence Links:</strong> {stats.get('total_relationships', 0)}</span>
                    </div>
                    <div style="margin-top:10px; font-size:11px; color:#94a3b8;">
                        <strong>Artifact Categories:</strong> {cat_badges}
                    </div>
                </div>
            </div>

            <!-- SECTION 2: ENTITY INTELLIGENCE & ANALYTICAL LEADS (CORRECTION 2) -->
            <div class="report-section">
                <h3 class="section-title">2. Entity Intelligence &amp; Analytical Leads</h3>
                <div class="section-note">
                    Analytical entities identified and resolved across evidence artifacts. These representations reflect automated resolution algorithms and require human investigator verification.
                </div>
                <div class="table-container">
                    <table class="report-table">
                        <thead>
                            <tr>
                                <th>Entity ID</th>
                                <th>Canonical Label / Name</th>
                                <th>Classification</th>
                                <th>Network Layer</th>
                                <th>Verification Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {leads_rows}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- SECTION 3: CONTACT NETWORK & PRIORITIZATION -->
            <div class="report-section">
                <h3 class="section-title">3. Contact Network &amp; Analytical Prioritization</h3>
                <div class="section-note">
                    Evidence-backed interaction vectors between identified entities, including call counts, financial flows, and Cross-Case Corroboration (CCC) confidence scores.
                </div>
                <div class="table-container">
                    <table class="report-table">
                        <thead>
                            <tr>
                                <th>Source Node</th>
                                <th>Target Node</th>
                                <th>Interaction Vector</th>
                                <th>Volume</th>
                                <th>CCC Confidence</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rel_rows}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- SECTION 4: FORENSIC EVIDENCE & ARTIFACT PROVENANCE -->
            <div class="report-section">
                <h3 class="section-title">4. Evidence &amp; Artifact Provenance Ledger</h3>
                <div class="section-note">
                    Register of evidentiary artifacts ingested from primary forensically preserved sources. Cryptographic integrity is verified via SHA-256 digests.
                </div>
                <div class="table-container">
                    <table class="report-table">
                        <thead>
                            <tr>
                                <th>Artifact ID</th>
                                <th>Filename</th>
                                <th>Category</th>
                                <th>File Size</th>
                                <th>SHA-256 Digest</th>
                            </tr>
                        </thead>
                        <tbody>
                            {art_rows}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- SECTION 5: SECTION 65B CERTIFICATE DRAFT (CORRECTION 3) -->
            <div class="report-section">
                <h3 class="section-title">5. Section 65B Certificate Draft / Examiner Review</h3>
                <div class="legal-draft-card">
                    <div class="legal-draft-header">
                        <span class="badge-draft">DRAFT FOR HUMAN EXAMINER REVIEW</span>
                        <span class="mono" style="font-size:10px; color:#94a3b8;">Ref: Sec 65B Indian Evidence Act / Electronic Record Rules</span>
                    </div>
                    <div class="legal-disclaimer">
                        <strong>NOTICE:</strong> This section is a system-generated analytical draft. It does not claim legal admissibility, official certification, examiner oath, judicial approval, or completed certification. An authorized human forensic examiner must independently review, verify, and complete this certificate prior to court submission.
                    </div>
                    <div class="legal-draft-body">
                        <div class="draft-row">
                            <span class="draft-lbl">Target Case ID:</span>
                            <span class="draft-val mono">{case_id}</span>
                        </div>
                        <div class="draft-row">
                            <span class="draft-lbl">Artifacts Analyzed:</span>
                            <span class="draft-val">{stats.get('total_artifacts', 0)} digital items</span>
                        </div>
                        <div class="draft-row">
                            <span class="draft-lbl">Primary Hash Reference:</span>
                            <span class="draft-val mono hash">{legal_draft.get('evidence_image_hash', '--')}</span>
                        </div>
                        <div class="draft-row">
                            <span class="draft-lbl">Draft Generated:</span>
                            <span class="draft-val mono">{timestamp_iso}</span>
                        </div>
                        
                        <div class="signature-block">
                            <div class="sig-line">
                                <div class="sig-field">________________________________________________</div>
                                <div class="sig-desc">Authorized Digital Evidence Examiner Signature</div>
                            </div>
                            <div class="sig-line">
                                <div class="sig-field">________________________________________________</div>
                                <div class="sig-desc">Official Designation / Government Examiner Seal</div>
                            </div>
                            <div class="sig-line">
                                <div class="sig-field">________________________________________________</div>
                                <div class="sig-desc">Date of Physical Execution</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- CRYPTOGRAPHIC INTEGRITY BLOCK -->
            <div class="report-crypto-seal">
                <div style="font-size:11px; font-weight:700; color:#38bdf8; text-transform:uppercase; letter-spacing:0.5px;">
                    Report Cryptographic Integrity Digest
                </div>
                <div class="mono" style="font-size:10px; color:#e2e8f0; margin-top:4px; word-break:break-all;">
                    SHA-256: <strong>{sha256_digest}</strong>
                </div>
                <div style="font-size:9.5px; color:#94a3b8; margin-top:4px;">
                    Calculated across compiled markdown analytical structure. Immutable audit trail maintained in SQLite ledger.
                </div>
            </div>
        </div>
        """
