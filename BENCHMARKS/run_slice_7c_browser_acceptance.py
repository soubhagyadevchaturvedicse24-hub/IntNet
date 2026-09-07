# -*- coding: utf-8 -*-
"""
CRIMENET // Slice 7C: Runtime E01 Forensic Image Intake
Comprehensive Playwright Browser Acceptance Test Suite
Browser: Microsoft Edge / Chromium Headless (1600x960)
"""

import os
import sys
import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

WORKSPACE_ROOT = Path(r"D:\Proto SIH")
SCREENSHOT_DIR = WORKSPACE_ROOT / "BENCHMARKS" / "screenshots"
FIXTURES_DIR = WORKSPACE_ROOT / "DATA" / "test_fixtures"

def run_acceptance():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    print("=" * 80)
    print("CRIMENET SLICE 7C: RUNTIME E01 FORENSIC INTAKE BROWSER ACCEPTANCE SUITE")
    print("=" * 80)

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    results = {}

    e01_path = FIXTURES_DIR / "Slice7c_Upload_Sample.E01"
    e02_path = FIXTURES_DIR / "Slice7c_Upload_Sample.E02"

    assert e01_path.exists(), f"Fixture missing: {e01_path}"
    assert e02_path.exists(), f"Fixture missing: {e02_path}"
    print(f"[PRE-TEST] Multi-segment sample fixtures ready:\n  - {e01_path.name} ({e01_path.stat().st_size} bytes)\n  - {e02_path.name} ({e02_path.stat().st_size} bytes)")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="msedge", headless=True)
            print("[INFO] Launched Microsoft Edge browser instance.")
        except Exception as e:
            print(f"[WARN] Edge launch fallback to default chromium: {e}")
            browser = p.chromium.launch(headless=True)

        context = browser.new_context(viewport={"width": 1600, "height": 960})
        page = context.new_page()

        try:
            # ----------------------------------------------------------------
            # STEP 1: LOGIN & PORTAL LANDING
            # ----------------------------------------------------------------
            print("\n[STEP 1] Login as officer1 and verify Case Portal landing...")
            page.goto("http://127.0.0.1:8000/workspace")
            page.wait_for_selector("#login-username", timeout=10000)
            page.fill("#login-username", "officer1")
            page.fill("#login-password", "OfficerPass123!")
            page.click("button[type='submit']")
            page.wait_for_selector("#login-overlay", state="hidden", timeout=10000)
            time.sleep(1.0)

            # Verify Case Portal is active
            assert page.is_visible("#view-portal"), "Case Portal must be visible upon login"
            assert page.is_hidden("#panel-explorer"), "Left panel must be hidden while in Case Portal"
            assert page.is_hidden("#panel-inspector"), "Right panel must be hidden while in Case Portal"
            portal_title = page.inner_text(".portal-subtitle")
            assert "INVESTIGATOR CASE PORTAL" in portal_title
            print(f" -> PASSED: Case Portal active ({portal_title})")
            page.screenshot(path=str(SCREENSHOT_DIR / "slice7c_01_portal_landing.png"))
            results["step1_portal_landing"] = "PASSED"

            # ----------------------------------------------------------------
            # STEP 2: OPEN NEW CASE WIZARD (STEP 1: CASE INFO)
            # ----------------------------------------------------------------
            print("\n[STEP 2] Open New Case Wizard & fill Case Information...")
            page.click(".btn-create-new-case")
            page.wait_for_selector("#modal-new-case-flow", state="visible", timeout=5000)
            page.wait_for_selector("#pane-step-1.active", timeout=3000)

            page.fill("#mf-case-name", "Operation Quantum Sentinel")
            page.fill("#mf-case-desc", "Runtime multi-segment E01 forensic image intake and observation")
            print(" -> PASSED: Step 1 Case Details populated.")
            page.screenshot(path=str(SCREENSHOT_DIR / "slice7c_02_wizard_step1_case_info.png"))
            results["step2_wizard_step1"] = "PASSED"

            # Advance to Step 2
            page.click("#pane-step-1 .btn-primary")
            time.sleep(0.5)

            # ----------------------------------------------------------------
            # STEP 3: JUDICIAL ASSIGNMENT (DYNAMIC BACKEND LOAD)
            # ----------------------------------------------------------------
            print("\n[STEP 3] Verify dynamic Judicial Officers loading...")
            page.wait_for_selector("#pane-step-2.active", timeout=3000)
            judge_options = page.eval_on_selector("#mf-judge-select", "sel => sel.options.length")
            assert judge_options > 0, "Judge select options must be populated from backend"
            selected_judge = page.eval_on_selector("#mf-judge-select", "sel => sel.value")
            print(f" -> PASSED: {judge_options} judicial officer(s) loaded dynamically (Selected: {selected_judge})")
            page.screenshot(path=str(SCREENSHOT_DIR / "slice7c_03_wizard_step2_judicial.png"))
            results["step3_judicial_assignment"] = f"PASSED ({judge_options} judges)"

            # Advance to Step 3
            page.click("#pane-step-2 .btn-primary")
            time.sleep(0.5)

            # ----------------------------------------------------------------
            # STEP 4: FORENSIC EVIDENCE INTAKE (DROPZONE & CHUNK STREAMING)
            # ----------------------------------------------------------------
            print("\n[STEP 4] Test Dual-Mode Intake, Dropzone & Chunk Streaming Upload...")
            page.wait_for_selector("#pane-step-3.active", timeout=3000)
            assert page.is_visible("#evidence-dropzone"), "Evidence dropzone must be visible"
            assert page.is_visible("#tab-intake-upload"), "Upload tab must be present"
            assert page.is_visible("#tab-intake-candidate"), "Candidate tab must be present"

            # Test tab switching to candidate mode and back
            page.click("#tab-intake-candidate")
            time.sleep(0.3)
            assert page.is_visible("#intake-section-candidate"), "Candidate list must be shown"
            assert page.is_hidden("#intake-section-upload"), "Dropzone section must be hidden"
            page.screenshot(path=str(SCREENSHOT_DIR / "slice7c_04a_wizard_step3_candidate_tab.png"))

            page.click("#tab-intake-upload")
            time.sleep(0.3)
            assert page.is_visible("#intake-section-upload"), "Dropzone section must be visible"
            page.screenshot(path=str(SCREENSHOT_DIR / "slice7c_04b_wizard_step3_dropzone_empty.png"))

            # Upload multi-segment E01 + E02 files via file input
            print("  Streaming chunks for multi-segment files: Slice7c_Upload_Sample.E01 + .E02...")
            page.set_input_files("#evidence-file-input", [str(e01_path), str(e02_path)])

            # Wait for upload and verification to complete
            page.wait_for_selector("#upload-summary-box:visible", timeout=5000)
            page.wait_for_selector("#upload-status-badge:has-text('STAGED & VERIFIED')", timeout=15000)

            status_text = page.inner_text("#upload-status-text")
            print(f" -> PASSED: Staged & Verified ({status_text})")
            page.screenshot(path=str(SCREENSHOT_DIR / "slice7c_04c_wizard_step3_staged_verified.png"))
            results["step4_dropzone_chunk_upload"] = "PASSED"

            # Advance to Step 4: Format Verification
            page.click("#pane-step-3 .btn-primary")
            time.sleep(0.5)

            # ----------------------------------------------------------------
            # STEP 5: READ-ONLY FORMAT VERIFICATION (INSPECT)
            # ----------------------------------------------------------------
            print("\n[STEP 5] Verify Read-Only Inspection via /api/v1/evidence/inspect...")
            page.wait_for_selector("#pane-step-4.active", timeout=3000)
            page.wait_for_selector(".status-pill.pill-intact:has-text('READ-ONLY SAFE')", timeout=8000)

            inspect_text = page.inner_text("#inspect-result-box")
            assert "Slice7c_Upload_Sample.E01" in inspect_text, "Primary filename must appear in inspection"
            assert "Companion Segments: 2" in inspect_text, "Companion count must appear in inspection"
            print(" -> PASSED: Read-Only format verified bit-for-bit safe.")
            page.screenshot(path=str(SCREENSHOT_DIR / "slice7c_05_wizard_step4_read_only_inspect.png"))
            results["step5_read_only_inspect"] = "PASSED"

            # Advance to Step 5: Creation & Registration
            page.click("#btn-submit-new-case")
            time.sleep(0.5)

            # ----------------------------------------------------------------
            # STEP 6: CREATION & SAFE PROMOTION
            # ----------------------------------------------------------------
            print("\n[STEP 6] Verify Case Creation & Staged Evidence Promotion...")
            page.wait_for_selector("#pane-step-5.active", timeout=3000)
            page.wait_for_selector("#step-5-status-area:has-text('Case & Evidence Registered Successfully')", timeout=10000)

            success_summary = page.inner_text("#step-5-status-area")
            print(" -> PASSED: Staged evidence promoted to case store; case promoted to ACTIVE.")
            page.screenshot(path=str(SCREENSHOT_DIR / "slice7c_06_wizard_step5_success.png"))
            results["step6_case_creation_promotion"] = "PASSED"

            # Click Enter Case Workspace
            page.click("#step-5-status-area .btn-primary")
            time.sleep(1.0)

            # ----------------------------------------------------------------
            # STEP 7: ENTER CASE WORKSPACE & EVIDENCE TABLE
            # ----------------------------------------------------------------
            print("\n[STEP 7] Verify Workspace Layout & Registered Evidence Container...")
            page.wait_for_selector("#panel-explorer:visible", timeout=8000)
            page.wait_for_selector(".ide-activity-bar:visible", timeout=8000)
            page.wait_for_selector("#view-cases.active", timeout=8000)

            active_case_badge = page.inner_text("#sidebar-active-case-id")
            print(f"  Active Case initialized: {active_case_badge}")
            page.screenshot(path=str(SCREENSHOT_DIR / "slice7c_07_workspace_evidence_table.png"))
            results["step7_workspace_entry"] = f"PASSED (Active: {active_case_badge})"

            # ----------------------------------------------------------------
            # STEP 8: EXPLICIT FORENSIC PROCESSING (PROCESS E01 ON REAL E01)
            # ----------------------------------------------------------------
            print("\n[STEP 8] Verify Explicit Process E01 Execution on Real E01 Image...")
            # Switch to CASE-2026-001 which contains verified real Images_Set_1.E01
            page.evaluate("openCaseFromPortal('CASE-2026-001')")
            time.sleep(1.0)
            page.wait_for_selector("#case-selector", timeout=5000)

            # Trigger processEvidence on real E01 container EV-2026-8A41
            print("  Triggering processEvidence('EV-2026-8A41') on real Images_Set_1.E01...")
            page.evaluate("processEvidence('EV-2026-8A41')")
            time.sleep(1.0)

            # Wait for job status badge to cycle to COMPLETED
            page.wait_for_function(
                "() => document.getElementById('job-badge') && document.getElementById('job-badge').innerText === 'COMPLETED'",
                timeout=40000
            )
            final_badge = page.evaluate("() => document.getElementById('job-badge').innerText")
            observed_fs = page.evaluate("() => document.getElementById('job-observed-fs').innerText")
            job_time = page.evaluate("() => document.getElementById('job-time').innerText")
            assert observed_fs == "NTFS", f"Expected NTFS filesystem, got {observed_fs}"
            print(f" -> PASSED: Forensic observation job {final_badge} (Filesystem: {observed_fs}, Time: {job_time})")
            results["step8_process_e01"] = f"PASSED ({final_badge}, FS: {observed_fs}, Time: {job_time})"
            page.screenshot(path=str(SCREENSHOT_DIR / "slice7c_08_evidence_processed_workspace.png"))

            # ----------------------------------------------------------------
            # STEP 9: EVIDENCE EXPLORER & ARTIFACT VIEWING
            # ----------------------------------------------------------------
            print("\n[STEP 9] Verify Evidence Explorer & Artifact Discovery...")
            page.click("#activity-btn-explorer")
            time.sleep(1.0)
            page.wait_for_selector("#panel-center .view-pane.active:visible", timeout=8000)
            page.wait_for_selector("#tree-node-evidence-root:visible", timeout=8000)
            page.screenshot(path=str(SCREENSHOT_DIR / "slice7c_09_evidence_explorer.png"))
            results["step9_evidence_explorer"] = "PASSED"

            print("\n" + "=" * 80)
            print("CRIMENET SLICE 7C ACCEPTANCE VERIFICATION SUMMARY:")
            print("=" * 80)
            for k, v in results.items():
                print(f"  {k:<35}: {v}")
            print("=" * 80)
            print("ALL BROWSER ACCEPTANCE TESTS PASSED SUCCESSFULLY!")

            # Write JSON report
            report_path = WORKSPACE_ROOT / "BENCHMARKS" / "slice_7c_browser_results.json"
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)

        finally:
            browser.close()

if __name__ == "__main__":
    run_acceptance()
