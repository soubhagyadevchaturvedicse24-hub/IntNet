"""
FastAPI REST Endpoints for CRIMENET Report Subsystem.
Exposes endpoints to list reports, generate live-data reports, view details, and download.
Enforces BOLA/BFLA authorization and logs audit events.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from typing import List, Optional

from src.auth.models import TokenPayload
from src.api.auth_routes import get_current_user, auth_service, policy_engine, audit_service
from src.api.case_routes import case_service
from src.artifacts.repository import SQLiteArtifactRepository
from src.parsers.repository import SQLiteParsedArtifactRepository
from src.api.graph_resolution_routes import entity_graph_service
from src.reports.models import (
    ReportDetail,
    ReportSummaryItem,
    ReportGenerateRequest
)
from src.reports.repository import SQLiteReportRepository
from src.reports.service import ReportService

router = APIRouter(prefix="/api/v1/cases/{case_id}/reports", tags=["Reports"])

# Initialize shared singleton ReportService
report_repository = SQLiteReportRepository()
artifact_repository = SQLiteArtifactRepository()
parsed_repository = SQLiteParsedArtifactRepository()

report_service = ReportService(
    repository=report_repository,
    case_service=case_service,
    artifact_repo=artifact_repository,
    parsed_repo=parsed_repository,
    entity_graph_service=entity_graph_service,
    policy_engine=policy_engine,
    audit_service=audit_service,
    auth_service=auth_service
)


@router.get("", response_model=List[ReportSummaryItem])
def list_case_reports(
    case_id: str,
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Lists all generated analytical reports for the specified case.
    Returns empty list if no reports have been generated yet.
    """
    try:
        return report_service.list_reports(current_user, case_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{report_id}", response_model=ReportDetail)
def get_case_report(
    case_id: str,
    report_id: str,
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Retrieves full details, markdown source, and rendered HTML of a specific report.
    """
    try:
        report = report_service.get_report(current_user, case_id, report_id)
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
        return report
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/generate", response_model=ReportDetail, status_code=status.HTTP_201_CREATED)
def generate_case_report(
    case_id: str,
    req: ReportGenerateRequest,
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Generates a new analytical report from LIVE case-scoped data.
    """
    try:
        return report_service.generate_report(current_user, case_id, req)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{report_id}/download")
def download_case_report(
    case_id: str,
    report_id: str,
    format: str = Query("html", pattern="^(html|markdown|md)$"),
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Downloads the report as an HTML file or Markdown document.
    """
    try:
        report = report_service.get_report(current_user, case_id, report_id)
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

        if format in ["markdown", "md"]:
            content = report.content_markdown
            media_type = "text/markdown; charset=utf-8"
            filename = f"{report.report_id}_{report.version}.md"
        else:
            # Standalone printable HTML page
            content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{report.title} - {report.version}</title>
<style>
    body {{ font-family: 'Inter', -apple-system, sans-serif; background: #fff; color: #0f172a; margin: 40px auto; max-width: 960px; line-height: 1.5; }}
    .mono {{ font-family: 'JetBrains Mono', monospace; }}
    .accent {{ color: #0284c7; }}
    .report-document {{ padding: 24px; }}
    .report-header-banner {{ border-bottom: 2px solid #0f172a; padding-bottom: 16px; margin-bottom: 20px; }}
    .report-header-top {{ display: flex; justify-content: space-between; align-items: center; }}
    .report-brand {{ display: flex; align-items: center; gap: 12px; }}
    .report-shield {{ font-size: 32px; }}
    .report-title-main {{ font-size: 20px; font-weight: 800; letter-spacing: -0.5px; }}
    .report-subtitle-main {{ font-size: 11px; color: #64748b; font-weight: 600; text-transform: uppercase; margin-top: 2px; }}
    .report-ver-badge {{ background: #0284c7; color: #fff; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 11px; }}
    .report-status-badge {{ background: #e2e8f0; color: #475569; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 11px; margin-left: 4px; }}
    .report-meta-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px; margin-bottom: 20px; font-size: 12px; }}
    .meta-label {{ color: #64748b; font-size: 10.5px; text-transform: uppercase; display: block; }}
    .report-section {{ margin-bottom: 24px; }}
    .section-title {{ font-size: 15px; font-weight: 700; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 10px; color: #0f172a; }}
    .section-note {{ font-size: 11.5px; color: #64748b; margin-bottom: 10px; font-style: italic; }}
    .report-table {{ width: 100%; border-collapse: collapse; font-size: 11.5px; margin-top: 8px; }}
    .report-table th {{ background: #f1f5f9; text-align: left; padding: 8px 10px; border-bottom: 2px solid #cbd5e1; font-weight: 600; }}
    .report-table td {{ padding: 8px 10px; border-bottom: 1px solid #e2e8f0; }}
    .badge-cat, .badge-role {{ background: #e0f2fe; color: #0369a1; padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 600; }}
    .badge-status {{ background: #fef3c7; color: #b45309; padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 600; }}
    .badge-ccc {{ background: #dcfce7; color: #15803d; padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 700; }}
    .stat-pill {{ background: #f1f5f9; padding: 4px 10px; border-radius: 20px; font-size: 11.5px; display: inline-block; }}
    .legal-draft-card {{ border: 1.5px dashed #f59e0b; background: #fffbeb; border-radius: 6px; padding: 16px; margin-top: 10px; }}
    .badge-draft {{ background: #f59e0b; color: #fff; font-size: 10px; font-weight: 800; padding: 2px 6px; border-radius: 3px; }}
    .legal-disclaimer {{ font-size: 11.5px; color: #92400e; margin: 10px 0; padding: 8px; background: rgba(245,158,11,0.1); border-radius: 4px; }}
    .draft-row {{ display: flex; gap: 10px; font-size: 12px; margin-bottom: 6px; }}
    .draft-lbl {{ font-weight: 600; min-width: 170px; }}
    .signature-block {{ margin-top: 24px; display: flex; justify-content: space-between; gap: 20px; }}
    .sig-line {{ flex: 1; }}
    .sig-field {{ font-family: monospace; color: #94a3b8; margin-bottom: 4px; }}
    .sig-desc {{ font-size: 11px; color: #64748b; font-weight: 600; }}
    .report-crypto-seal {{ border-top: 2px solid #0f172a; padding-top: 12px; margin-top: 30px; font-size: 11px; color: #475569; }}
    @media print {{
        body {{ margin: 0; }}
        .report-document {{ padding: 0; }}
    }}
</style>
</head>
<body>
{report.content_html}
<script>
    // Automatic print dialog if requested
    if (window.location.search.includes('autoprint=true')) {{
        window.print();
    }}
</script>
</body>
</html>"""
            media_type = "text/html; charset=utf-8"
            filename = f"{report.report_id}_{report.version}.html"

        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
