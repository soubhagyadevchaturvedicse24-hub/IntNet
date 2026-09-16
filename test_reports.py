"""
Targeted Test Suite for CRIMENET Reports Domain.
Tests listing, live generation, versioning, cryptographic SHA-256 integrity,
Section 65B Draft review, and download.
"""

import sys
import os

from fastapi.testclient import TestClient
from src.api.main import app
from src.auth.service import AuthService
from src.reports.repository import SQLiteReportRepository

client = TestClient(app)
auth_service = AuthService()

def test_reports_workflow():
    print("=== Testing Reports Domain Workflow ===")
    
    # 1. Login as investigator
    user = auth_service.get_user_by_id("USER-OFFICER-001")
    token = auth_service.create_access_token(user)
    headers = {"Authorization": f"Bearer {token}"}
    
    case_id = "CASE-2026-001"
    
    # 2. List reports before any generation: MUST BE EMPTY (Correction 1)
    # Clear any leftover test data in SQLite repository for CASE-2026-001
    repo = SQLiteReportRepository()
    with repo._lock:
        repo._conn.execute("DELETE FROM case_reports WHERE case_id = ?", (case_id,))
        repo._conn.commit()

    res = client.get(f"/api/v1/cases/{case_id}/reports", headers=headers)
    assert res.status_code == 200, f"List failed: {res.text}"
    reports_init = res.json()
    print(f"[PASS] Initial reports for {case_id}: {len(reports_init)} (Strictly empty, no fake reports)")
    assert len(reports_init) == 0, "Should be 0 reports for clean case"

    # 3. Generate first report (v1.0)
    gen_payload = {
        "template_type": "COMPREHENSIVE_DOSSIER",
        "title": "Comprehensive Evidence & Entity Dossier",
        "notes": "Verified against isolated evidence store EV-2026-001.",
        "include_deleted": True,
        "include_unverified": True
    }
    res_gen = client.post(f"/api/v1/cases/{case_id}/reports/generate", json=gen_payload, headers=headers)
    assert res_gen.status_code == 201, f"Generation failed: {res_gen.text}"
    rep1 = res_gen.json()
    print(f"[PASS] Generated report 1: ID={rep1['report_id']}, Version={rep1['version']}, SHA-256={rep1['sha256'][:16]}...")
    assert rep1["version"] == "v1.0"
    assert rep1["version_number"] == 1
    assert rep1["previous_version_id"] is None
    assert rep1["is_current"] is True
    assert "CRIMENET Forensic Investigation Report" in rep1["content_markdown"]
    assert "System-generated analytical report — Human review required" in rep1["content_markdown"]
    assert "Entity Intelligence & Analytical Leads" in rep1["content_markdown"]
    assert "Section 65B Certificate Draft / Examiner Review" in rep1["content_markdown"]
    assert "DRAFT FOR HUMAN EXAMINER REVIEW" in rep1["content_markdown"]
    assert rep1["sha256"] is not None and len(rep1["sha256"]) == 64

    # 4. Generate second report (v2.0)
    gen_payload2 = {
        "template_type": "EXECUTIVE_BRIEF",
        "title": "Executive Analytical Summary",
        "notes": "Follow-up triage for judicial review.",
        "include_deleted": False,
        "include_unverified": True
    }
    res_gen2 = client.post(f"/api/v1/cases/{case_id}/reports/generate", json=gen_payload2, headers=headers)
    assert res_gen2.status_code == 201, f"Generation 2 failed: {res_gen2.text}"
    rep2 = res_gen2.json()
    print(f"[PASS] Generated report 2: ID={rep2['report_id']}, Version={rep2['version']}, PrevID={rep2['previous_version_id']}")
    assert rep2["version"] == "v2.0"
    assert rep2["version_number"] == 2
    assert rep2["previous_version_id"] == rep1["report_id"]
    assert rep2["is_current"] is True

    # 5. Verify list now returns both versions, with rep2 as current
    res_list = client.get(f"/api/v1/cases/{case_id}/reports", headers=headers)
    assert res_list.status_code == 200
    reports_list = res_list.json()
    print(f"[PASS] Total reports now in case: {len(reports_list)}")
    assert len(reports_list) == 2
    assert reports_list[0]["report_id"] == rep2["report_id"]
    assert reports_list[0]["is_current"] is True
    assert reports_list[1]["report_id"] == rep1["report_id"]
    assert reports_list[1]["is_current"] is False

    # 6. Retrieve single report by ID
    res_get = client.get(f"/api/v1/cases/{case_id}/reports/{rep1['report_id']}", headers=headers)
    assert res_get.status_code == 200
    rep1_fetched = res_get.json()
    assert rep1_fetched["report_id"] == rep1["report_id"]
    print(f"[PASS] Fetched single report {rep1['report_id']} successfully.")

    # 7. Download report as Markdown & HTML
    res_dl_md = client.get(f"/api/v1/cases/{case_id}/reports/{rep1['report_id']}/download?format=markdown", headers=headers)
    assert res_dl_md.status_code == 200
    assert "attachment" in res_dl_md.headers.get("Content-Disposition", "")
    assert res_dl_md.text.startswith("# CRIMENET Forensic Investigation Report")
    print(f"[PASS] Downloaded report as Markdown ({len(res_dl_md.text)} bytes).")

    res_dl_html = client.get(f"/api/v1/cases/{case_id}/reports/{rep1['report_id']}/download?format=html", headers=headers)
    assert res_dl_html.status_code == 200
    assert "<!DOCTYPE html>" in res_dl_html.text
    print(f"[PASS] Downloaded report as HTML ({len(res_dl_html.text)} bytes).")

    # 8. Test live case CASE-2026-E2D4 with real graph entities & links
    e2d4_case = "CASE-2026-E2D4"
    with repo._lock:
        repo._conn.execute("DELETE FROM case_reports WHERE case_id = ?", (e2d4_case,))
        repo._conn.commit()

    res_e2d4 = client.get(f"/api/v1/cases/{e2d4_case}/reports", headers=headers)
    assert res_e2d4.status_code == 200
    assert len(res_e2d4.json()) == 0
    print(f"[PASS] CASE-2026-E2D4 initial reports: 0 (Honest empty state)")

    res_gen_e2d4 = client.post(f"/api/v1/cases/{e2d4_case}/reports/generate", json={
        "template_type": "COMPREHENSIVE_DOSSIER",
        "title": "Operation Dark Phoenix Comprehensive Forensic Dossier",
        "notes": "Compiled from live disk image evidence and Kùzu contact graph.",
        "include_deleted": True,
        "include_unverified": True
    }, headers=headers)
    assert res_gen_e2d4.status_code == 201
    rep_e2d4 = res_gen_e2d4.json()
    print(f"[PASS] Generated live report for {e2d4_case}: Version={rep_e2d4['version']}, Artifacts={rep_e2d4['stats']['total_artifacts']}, Entities={rep_e2d4['stats']['total_entities']}, Links={rep_e2d4['stats']['total_relationships']}")
    assert rep_e2d4["stats"]["total_artifacts"] == 91
    assert rep_e2d4["stats"]["total_entities"] == 24
    assert rep_e2d4["stats"]["total_relationships"] == 21
    assert "Entity Intelligence & Analytical Leads" in rep_e2d4["content_markdown"]
    assert "Section 65B Certificate Draft / Examiner Review" in rep_e2d4["content_markdown"]

    print("\n=== ALL REPORTS DOMAIN TARGETED TESTS PASSED ===")

if __name__ == "__main__":
    test_reports_workflow()
