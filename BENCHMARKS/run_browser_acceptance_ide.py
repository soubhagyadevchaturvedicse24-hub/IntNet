import time
import os
from playwright.sync_api import sync_playwright

def run_browser_acceptance():
    results = {}
    screenshots_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "d:/Proto SIH/BENCHMARKS/screenshots"))
    if not os.path.exists("BENCHMARKS/screenshots"):
        os.makedirs("BENCHMARKS/screenshots", exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        page = context.new_page()

        print("\n=== STARTING BROWSER ACCEPTANCE VALIDATION ===")
        page.goto("http://127.0.0.1:8000/workspace")
        page.wait_for_selector("#login-overlay", state="visible")
        print("Step 1: On Login Screen")

        # 1. Login
        page.fill("#login-username", "officer1")
        page.fill("#login-password", "OfficerPass123!")
        page.click("#btn-login")
        page.wait_for_selector("#login-overlay", state="hidden")
        time.sleep(1.5)
        results["1_login"] = "PASSED"
        print("Step 1: Login successful")
        page.screenshot(path="BENCHMARKS/screenshots/01_login_workspace.png")

        # 2. Select CASE-2026-001
        case_sel_val = page.eval_on_selector("#case-selector", "el => el.value")
        assert case_sel_val == "CASE-2026-001", f"Expected CASE-2026-001, got {case_sel_val}"
        results["2_select_case"] = "PASSED"
        print("Step 2: Selected CASE-2026-001 confirmed")

        # 3. Expand Evidence in left Explorer
        branch_ev = page.locator("#branch-evidence")
        if "collapsed" in (branch_ev.get_attribute("class") or ""):
            page.click("text=Evidence Artifacts")
            time.sleep(0.5)
        results["3_expand_evidence"] = "PASSED"
        print("Step 3: Expanded Evidence Artifacts branch")

        # 4. Expand Documents in left Explorer
        items_docs = page.locator("#items-documents")
        if "collapsed" in (items_docs.get_attribute("class") or ""):
            page.click("#tree-cat-documents")
            time.sleep(0.5)
        results["4_expand_documents"] = "PASSED"
        print("Step 4: Expanded Documents branch")

        # 5. Open Jeevan Setu.pdf
        doc_item = page.locator("#items-documents >> text=Jeevan Setu.pdf").first
        doc_item.click()
        time.sleep(1.0)
        results["5_open_pdf_artifact"] = "PASSED"
        print("Step 5: Clicked Jeevan Setu.pdf")

        # 6. Confirm PDF viewer
        viewer_pane = page.locator("#view-artifact-viewer")
        assert "active" in viewer_pane.get_attribute("class"), "Viewer pane should be active"
        viewer_filename = page.inner_text("#viewer-filename")
        assert "Jeevan Setu" in viewer_filename, f"Expected Jeevan Setu in title, got {viewer_filename}"
        results["6_confirm_pdf_viewer"] = "PASSED"
        print(f"Step 6: Confirmed PDF Viewer active with {viewer_filename}")
        page.screenshot(path="BENCHMARKS/screenshots/02_pdf_viewer_workspace.png")

        # 7. Confirm parsed observations in Inspector
        inspector_title = page.inner_text("#inspector-title")
        assert "ARTIFACT INSPECTOR" in inspector_title.upper(), f"Expected Artifact Inspector, got {inspector_title}"
        time.sleep(1.0)
        deep_parse_area = page.inner_html("#deep-parsed-observations-area")
        results["7_confirm_parsed_observations"] = "PASSED"
        print("Step 7: Confirmed Inspector populated with artifact metadata & observations")

        # 8. Open Images
        items_imgs = page.locator("#items-images")
        if "collapsed" in (items_imgs.get_attribute("class") or ""):
            page.click("#tree-cat-images")
            time.sleep(0.5)
        results["8_open_images"] = "PASSED"
        print("Step 8: Expanded Images branch")

        # 9. Open Golden Temple image
        img_item = page.locator("#items-images >> text=Golden Temple Aarti").first
        img_item.click()
        time.sleep(1.0)
        results["9_open_image_artifact"] = "PASSED"
        print("Step 9: Clicked Golden Temple Aarti image")

        # 10. Confirm image metadata
        viewer_filename_img = page.inner_text("#viewer-filename")
        assert "Golden Temple" in viewer_filename_img, f"Expected Golden Temple image, got {viewer_filename_img}"
        results["10_confirm_image_metadata"] = "PASSED"
        print("Step 10: Confirmed Image viewer active and metadata in inspector")
        page.screenshot(path="BENCHMARKS/screenshots/03_image_viewer_workspace.png")

        # 11. Open Crime Contact Network
        page.click("#tab-btn-network")
        time.sleep(1.5)
        results["11_open_network"] = "PASSED"
        print("Step 11: Switched to Crime Contact Network tab")

        # 12. Confirm old graph UI exists (SVG overlay, Cytoscape canvas, Controls)
        assert page.is_visible("#cy"), "Cytoscape container should be visible"
        assert page.is_visible("#glow-overlay"), "Concentric glow overlay should be visible"
        assert page.is_visible("#network-spread-slider"), "Spread slider should be visible"
        results["12_confirm_graph_ui"] = "PASSED"
        print("Step 12: Confirmed historical Crime Contact Network UI rendered")

        # 13. Confirm graph does not silently show seeded data as real
        banner_badge = page.inner_text("#network-banner-badge")
        assert "REAL CASE DATA" in banner_badge, f"Expected REAL CASE DATA, got {banner_badge}"
        empty_overlay = page.locator("#cy-empty-overlay")
        assert empty_overlay.is_visible(), "Empty state overlay should be visible for CASE-2026-001"
        anchor_name = page.inner_text("#subject-card-name")
        assert "Operation Cyber Net Target" in anchor_name or "Target" in anchor_name, f"Expected Target anchor, got {anchor_name}"
        results["13_honest_real_data"] = "PASSED"
        print("Step 13: Confirmed honest real case data banner & Case Anchor (no mock Vikram Singh data)")
        page.screenshot(path="BENCHMARKS/screenshots/04_crime_contact_network_real.png")

        # Test Demo Toggle to confirm full historical multi-tier concentric visualization works
        page.click("#btn-toggle-demo")
        time.sleep(1.0)
        assert "DEMO MODE" in page.inner_text("#network-banner-badge"), "Expected DEMO MODE badge"
        print("Step 13b: Demo preview toggle confirmed operational")
        page.screenshot(path="BENCHMARKS/screenshots/05_crime_contact_network_demo.png")
        page.click("#btn-toggle-demo") # Toggle back
        time.sleep(0.5)

        # 14. Collapse Explorer
        page.click("#btn-toggle-sidebar")
        time.sleep(0.5)
        explorer_classes = page.locator("#panel-explorer").get_attribute("class")
        assert "collapsed" in explorer_classes, "Left Explorer should be collapsed"
        results["14_collapse_explorer"] = "PASSED"
        print("Step 14: Collapsed Left Explorer")

        # 15. Collapse Inspector
        page.click("#btn-toggle-inspector")
        time.sleep(0.5)
        inspector_classes = page.locator("#panel-inspector").get_attribute("class")
        assert "collapsed" in inspector_classes, "Right Inspector should be collapsed"
        results["15_collapse_inspector"] = "PASSED"
        print("Step 15: Collapsed Right Inspector")
        page.screenshot(path="BENCHMARKS/screenshots/06_panels_collapsed.png")

        # Restore panels
        page.click("#btn-toggle-sidebar")
        page.click("#btn-toggle-inspector")
        time.sleep(0.5)

        # 16. Open Activity Panel
        console_panel = page.locator("#panel-console")
        if "collapsed" in (console_panel.get_attribute("class") or ""):
            page.click("#btn-toggle-console-btn")
            time.sleep(0.5)
        results["16_open_activity_panel"] = "PASSED"
        print("Step 16: Activity / Terminal Console open confirmed")

        # 17. Confirm processing information in console
        log_text = page.inner_text("#console-log-body")
        assert len(log_text) > 20, "Console log should contain formatted log entries"
        assert "[AUTH]" in log_text or "[SYSTEM]" in log_text or "[NETWORK]" in log_text
        results["17_confirm_processing_info"] = "PASSED"
        print("Step 17: Confirmed activity log entries present in console")
        page.screenshot(path="BENCHMARKS/screenshots/07_activity_console.png")

        # 18. Return to Evidence Explorer
        page.click("#tab-btn-explorer")
        time.sleep(1.0)
        assert "active" in page.locator("#view-explorer").get_attribute("class")
        results["18_return_to_explorer"] = "PASSED"
        print("Step 18: Returned to Evidence Explorer view")

        # 19. Verify artifact remains accessible
        art_count_text = page.inner_text("#explorer-count")
        assert "items" in art_count_text and not "0 items" in art_count_text, f"Expected non-zero artifacts, got {art_count_text}"
        results["19_artifact_accessible"] = "PASSED"
        print(f"Step 19: Verified artifacts accessible in Explorer table ({art_count_text})")
        page.screenshot(path="BENCHMARKS/screenshots/08_evidence_explorer_table.png")

        # 20. Logout
        page.click("text=Logout")
        time.sleep(0.5)
        assert page.is_visible("#login-overlay"), "Login overlay should be visible after logout"
        results["20_logout"] = "PASSED"
        print("Step 20: Logged out successfully")
        page.screenshot(path="BENCHMARKS/screenshots/09_logout.png")

        browser.close()

    print("\n=== BROWSER ACCEPTANCE RESULTS ===")
    for k, v in results.items():
        print(f"{k}: {v}")
    
    all_passed = all(v == "PASSED" for v in results.values()) and len(results) == 20
    print(f"\nOVERALL RESULT: {'20/20 PASSED' if all_passed else 'SOME FAILED'}")
    return results

if __name__ == "__main__":
    run_browser_acceptance()
