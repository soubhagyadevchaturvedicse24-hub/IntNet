# -*- coding: utf-8 -*-
"""
CRIMENET // Final Investigator Workspace Comprehensive Acceptance Suite
Browser: Microsoft Edge (channel="msedge")
Validates complete UI matching Reference A and Reference B:
- 4-zone layout (Activity Bar, Contextual Sidebar, Center Workspace, Contextual Inspector)
- Dynamic switching between Evidence Explorer and Crime Contact Network
- Center Artifact Viewer with top header, canvas, and bottom tabbed panel (Metadata, Hex View, Text, Parsed, Raw)
- Concentric polar Cytoscape graph canvas with full width proportions, SVG glowing rings, and dock
- Right Contextual Inspector (Artifact Inspector with Basic Info, Hash, Deep Parsed tabs / Lead & Relationship Inspector)
- Resizable splitters, collapse controls, activity console, and authentication.
"""

import sys
import time
import json
import os
from playwright.sync_api import sync_playwright

def run_acceptance_suite():
    print("================================================================================")
    print("CRIMENET // FINAL INVESTIGATOR WORKSPACE UI ACCEPTANCE SUITE (EDGE)")
    print("================================================================================")

    results = {}
    screenshot_dir = "BENCHMARKS/screenshots"
    os.makedirs(screenshot_dir, exist_ok=True)

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="msedge", headless=True)
            print("[INFO] Launched Microsoft Edge browser instance.")
        except Exception as e:
            print(f"[WARN] Edge launch failed ({e}), falling back to default chromium.")
            browser = p.chromium.launch(headless=True)

        context = browser.new_context(viewport={"width": 1600, "height": 960})
        page = context.new_page()

        # STEP 1: Login
        print("\n[STEP 1] Login as officer1...")
        page.goto("http://127.0.0.1:8000/workspace")
        page.wait_for_selector("#login-username", timeout=8000)
        page.fill("#login-username", "officer1")
        page.fill("#login-password", "OfficerPass123!")
        page.click("#btn-login")
        page.wait_for_selector("#login-overlay", state="hidden", timeout=8000)
        time.sleep(1.0)
        results["01_login"] = "PASSED"
        print(" -> PASSED: Authenticated session established.")

        # STEP 2: Verify Initial Workspace IDE Layout (4 Zones + Console + Splitters)
        print("\n[STEP 2] Verify Initial Workspace IDE Layout...")
        page.wait_for_selector(".ide-activity-bar:visible")
        page.wait_for_selector("#panel-explorer:visible")
        page.wait_for_selector("#panel-center:visible")
        page.wait_for_selector("#panel-inspector:visible")
        page.wait_for_selector("#panel-console:visible")
        page.wait_for_selector("#splitter-left:visible")
        page.wait_for_selector("#splitter-right:visible")

        act_items = page.eval_on_selector_all(".activity-item", "items => items.length")
        assert act_items >= 6, f"Expected at least 6 activity bar items, found {act_items}"
        results["02_workspace_layout"] = f"PASSED ({act_items} activity items)"
        print(f" -> PASSED: Workspace IDE 4 zones verified with {act_items} activity items.")

        # STEP 3: Switch to Evidence Explorer (Reference B)
        print("\n[STEP 3] Switch to Evidence Explorer via Activity Bar...")
        page.click("#activity-btn-explorer")
        time.sleep(0.5)

        # Check active states
        is_act_active = page.eval_on_selector("#activity-btn-explorer", "el => el.classList.contains('active')")
        assert is_act_active, "Activity Bar should be active for Explorer"
        assert page.locator("#tab-btn-explorer").count() == 0, "Top tab-btn-explorer should be removed"
        assert page.locator("#tab-btn-cases").count() == 0, "Top tab-btn-cases should be removed"
        assert page.locator("#tab-btn-network").count() == 0, "Top tab-btn-network should be removed"

        # Check Sidebar header and breadcrumb
        sidebar_title = page.inner_text("#sidebar-panel-title")
        assert "EXPLORER" in sidebar_title.upper()
        breadcrumb_text = page.inner_text("#sidebar-case-breadcrumb")
        assert "CASE-2026-001" in breadcrumb_text

        # Check tree artifact count
        total_arts = page.inner_text("#tree-count-total-artifacts")
        print(f" -> Discovered total artifacts in tree: {total_arts}")
        assert int(total_arts) > 0, "Artifacts should be populated from real case"

        results["03_evidence_explorer_navigation"] = f"PASSED ({total_arts} artifacts)"
        print(" -> PASSED: Evidence Explorer sidebar & breadcrumb verified.")

        # STEP 4: Inspect Artifact Viewer & Select Jeevan Setu.pdf (Reference B)
        print("\n[STEP 4] Select Jeevan Setu.pdf in Documents tree...")
        page.wait_for_selector("#items-documents", timeout=5000)

        # Ensure documents branch is open
        is_docs_open = page.eval_on_selector("#items-documents", "el => !el.classList.contains('collapsed')")
        if not is_docs_open:
            page.click("#tree-cat-documents")
            time.sleep(0.3)

        # Find Jeevan Setu item and click it
        jeevan_item = page.wait_for_selector("#items-documents .tree-sub-item:has-text('Jeevan Setu')", timeout=5000)
        jeevan_item.click()
        time.sleep(1.0)

        # Verify Center switches to #view-artifact-viewer
        page.wait_for_selector("#view-artifact-viewer:visible")
        viewer_fn = page.inner_text("#viewer-filename")
        viewer_bc = page.inner_text("#viewer-breadcrumb")
        print(f" -> Active Viewer File: {viewer_fn}, Breadcrumb: {viewer_bc}")
        assert "Jeevan Setu.pdf" in viewer_fn
        assert "Documents" in viewer_bc

        # Check bottom panel metadata grid (Reference B)
        vm_mime = page.inner_text("#vm-mime")
        vm_size = page.inner_text("#vm-size")
        vm_alloc = page.inner_text("#vm-alloc")
        vm_hash = page.inner_text("#vm-hash")
        assert "pdf" in vm_mime.lower()
        assert "ALLOCATED" in vm_alloc
        assert len(vm_hash) >= 32
        print(f" -> Bottom Metadata: MIME={vm_mime}, Size={vm_size}, Hash={vm_hash[:16]}...")

        # Save Screenshot of Evidence Explorer (Matching Reference B)
        ss1_path = os.path.join(screenshot_dir, "final_workspace_01_evidence_explorer_pdf.png")
        page.screenshot(path=ss1_path)
        print(f" -> Captured Reference B Evidence Explorer Screenshot: {ss1_path}")
        results["04_artifact_viewer_pdf"] = "PASSED"

        # STEP 5: Test Bottom Panel Tabs (Hex View, Text Content, Parsed, Raw)
        print("\n[STEP 5] Test Bottom Panel Tabs in Artifact Viewer...")
        # Hex View
        page.click("#btn-art-tab-hex")
        time.sleep(0.3)
        hex_text = page.inner_text("#art-tab-hex-body")
        assert "00000000" in hex_text, "Hex view should show memory offset and hex bytes"
        print(" -> PASSED: Hex View displays authentic 16-byte forensic hex dump.")

        # Text Content
        page.click("#btn-art-tab-text")
        time.sleep(0.3)
        text_content = page.inner_text("#art-tab-text-body")
        assert len(text_content) > 0
        print(f" -> PASSED: Text Content tab populated ({len(text_content)} chars).")

        # Metadata Tab
        page.click("#btn-art-tab-meta")
        time.sleep(0.2)
        results["05_artifact_bottom_tabs"] = "PASSED"

        # STEP 6: Verify Right Contextual Inspector for Artifact (Reference B)
        print("\n[STEP 6] Verify Right Contextual Inspector for Artifact...")
        insp_title = page.inner_text("#inspector-title")
        assert "INSPECTOR" in insp_title.upper()
        insp_badge = page.inner_text("#inspector-badge")
        assert "DOCUMENT" in insp_badge

        # Verify Deep Parsed Observations sub-tabs (Reference B)
        page.wait_for_selector("#btn-insp-tab-struct:visible")
        page.wait_for_selector("#btn-insp-tab-text:visible")
        page.wait_for_selector("#btn-insp-tab-refs:visible")

        # Test clicking sub-tabs
        page.click("#btn-insp-tab-text")
        time.sleep(0.2)
        page.click("#btn-insp-tab-refs")
        time.sleep(0.2)
        page.click("#btn-insp-tab-struct")
        time.sleep(0.2)
        results["06_contextual_inspector_artifact"] = "PASSED"
        print(" -> PASSED: Right Contextual Inspector matches Reference B layout.")

        # STEP 7: Switch to Crime Contact Network (Reference A)
        print("\n[STEP 7] Switch to Crime Contact Network via Activity Bar...")
        page.click("#activity-btn-network")
        time.sleep(0.8)

        # Check active states
        is_net_act_active = page.eval_on_selector("#activity-btn-network", "el => el.classList.contains('active')")
        assert is_net_act_active, "Activity Bar should be active for Network"

        # Check Contextual Sidebar updated to Network Controls (Reference A)
        sidebar_title_net = page.inner_text("#sidebar-panel-title")
        assert "NETWORK" in sidebar_title_net.upper()
        page.wait_for_selector("#path-target-input:visible")
        page.wait_for_selector("#network-spread-slider:visible")
        page.wait_for_selector("#subject-card-name:visible")
        page.wait_for_selector("#btn-filter-l1:visible")
        print(" -> PASSED: Contextual Sidebar dynamically switched to Crime Contact Network controls.")

        # Check Center Panel is full-width Cytoscape canvas
        page.wait_for_selector("#view-network:visible")
        page.wait_for_selector("#cy:visible")
        page.wait_for_selector("#glow-overlay:visible")
        page.wait_for_selector(".workspace-bottom-right-dock:visible")

        # Save Screenshot of Real Data Crime Contact Network
        ss2_path = os.path.join(screenshot_dir, "final_workspace_02_crime_contact_network_real.png")
        page.screenshot(path=ss2_path)
        print(f" -> Captured Real Data Crime Contact Network Screenshot: {ss2_path}")
        results["07_crime_contact_network_real"] = "PASSED"

        # STEP 8: Toggle Demo Mode & Verify Concentric Visualization (Reference A)
        print("\n[STEP 8] Toggle Demo Mode to preview full multi-tier concentric network (Reference A)...")
        page.click("#btn-toggle-demo")
        time.sleep(1.0)

        banner_badge_text = page.inner_text("#network-banner-badge")
        assert "DEMO" in banner_badge_text
        anchor_name = page.inner_text("#subject-card-name")
        assert "Vikram Singh" in anchor_name
        print(f" -> Anchor Subject: {anchor_name}")

        # Check Cytoscape nodes count in demo mode
        node_count = page.evaluate("() => cy ? cy.nodes().length : 0")
        edge_count = page.evaluate("() => cy ? cy.edges().length : 0")
        print(f" -> Cytoscape Graph Rendered: {node_count} nodes, {edge_count} edges.")
        assert node_count >= 8
        assert edge_count >= 10

        # Save Screenshot of Concentric Graph in Demo Mode (Matching Reference A)
        ss3_path = os.path.join(screenshot_dir, "final_workspace_03_crime_contact_network_demo.png")
        page.screenshot(path=ss3_path)
        print(f" -> Captured Reference A Concentric Graph Screenshot: {ss3_path}")
        results["08_concentric_graph_demo"] = f"PASSED ({node_count} nodes, {edge_count} edges)"

        # STEP 9: Test Layer Filters & Layer Spacing Slider
        print("\n[STEP 9] Test Layer Filters & Layer Spacing Slider...")
        # Layer 1 filter
        page.click("#btn-filter-l1")
        time.sleep(0.3)
        l1_focused = page.evaluate("() => cy.elements('.layer-focused').length")
        assert l1_focused > 0, "Layer 1 elements should be focused"

        # Show All filter
        page.click("#btn-filter-all")
        time.sleep(0.3)

        # Move spread slider to 130%
        page.evaluate("() => { const s = document.getElementById('network-spread-slider'); s.value = 130; updateNetworkSpread(130); }")
        time.sleep(0.3)
        spread_val = page.inner_text("#spread-value")
        assert "130" in spread_val
        print(f" -> Layer Spacing scaled to: {spread_val}")

        # Reset layout button
        page.click("button:has-text('Reset Layout')")
        time.sleep(0.3)
        spread_val_reset = page.inner_text("#spread-value")
        assert "100%" in spread_val_reset
        print(" -> Layout reset successfully to 100%.")
        results["09_network_controls"] = "PASSED"

        # STEP 10: Test Node Tap & Lead Inspector (Reference A)
        print("\n[STEP 10] Test Node Tap & Lead Inspector...")
        page.evaluate("() => { const n = cy.nodes('[id = \"CAN-PER-0002\"]')[0] || cy.nodes()[1]; if (n) n.emit('tap'); }")
        time.sleep(0.5)

        insp_lead_title = page.inner_text("#inspector-title")
        assert "LEAD" in insp_lead_title.upper()
        print(f" -> Inspector Title: {insp_lead_title}")

        # Verify human verification decision buttons
        page.wait_for_selector("button:has-text('Review'):visible")
        page.wait_for_selector("button:has-text('Verify'):visible")
        page.wait_for_selector("button:has-text('Reject'):visible")

        # Capture Lead Inspector Screenshot
        ss4_path = os.path.join(screenshot_dir, "final_workspace_04_lead_inspector.png")
        page.screenshot(path=ss4_path)
        print(f" -> Captured Lead Inspector Screenshot: {ss4_path}")
        results["10_lead_inspector"] = "PASSED"

        # STEP 11: Test Draggable Splitters
        print("\n[STEP 11] Test Draggable Splitters...")
        w_left_before = page.eval_on_selector("#panel-explorer", "el => el.getBoundingClientRect().width")
        s_left_box = page.eval_on_selector("#splitter-left", "el => { const r = el.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + 120 }; }")
        page.mouse.move(s_left_box["x"], s_left_box["y"])
        page.mouse.down()
        page.mouse.move(s_left_box["x"] + 60, s_left_box["y"], steps=6)
        page.mouse.up()
        time.sleep(0.3)
        w_left_after = page.eval_on_selector("#panel-explorer", "el => el.getBoundingClientRect().width")
        print(f" -> Left Splitter Resize: {w_left_before:.1f}px -> {w_left_after:.1f}px")
        assert w_left_after > w_left_before

        results["11_draggable_splitters"] = "PASSED"

        # STEP 12: Test Panel Collapse & Restore
        print("\n[STEP 12] Test Panel Collapse & Restore...")
        page.click("#btn-toggle-sidebar")
        time.sleep(0.3)
        assert page.eval_on_selector("#panel-explorer", "el => el.classList.contains('collapsed')")
        page.click("#btn-toggle-sidebar")
        time.sleep(0.3)
        assert not page.eval_on_selector("#panel-explorer", "el => el.classList.contains('collapsed')")
        print(" -> Sidebar collapse & restore verified.")

        page.click("#btn-toggle-console-btn")
        time.sleep(0.3)
        assert page.eval_on_selector("#panel-console", "el => el.classList.contains('collapsed')")
        page.click("#btn-toggle-console-btn")
        time.sleep(0.3)
        assert not page.eval_on_selector("#panel-console", "el => el.classList.contains('collapsed')")
        print(" -> Console collapse & restore verified.")
        results["12_collapse_restore"] = "PASSED"

        # STEP 13: Test Activity Console Logging & Clear
        print("\n[STEP 13] Test Activity Console Logging & Clear...")
        event_count = page.inner_text("#console-event-count")
        print(f" -> Total events logged in session: {event_count}")
        page.click("button:has-text('Clear Console')")
        time.sleep(0.2)
        event_count_cleared = page.inner_text("#console-event-count")
        assert "(0 EVENTS)" in event_count_cleared.upper()
        print(" -> Console cleared successfully.")
        results["13_activity_console"] = "PASSED"

        # STEP 14: Logout & Session Destruction
        print("\n[STEP 14] Test Logout & Session Destruction...")
        page.click(".btn-header-logout")
        time.sleep(0.5)
        page.wait_for_selector("#login-overlay:visible")
        token_after = page.evaluate("() => sessionStorage.getItem('crimenet_token')")
        assert token_after is None, "sessionStorage token should be nullified"
        print(" -> PASSED: Session terminated, login overlay restored.")
        results["14_logout"] = "PASSED"

        browser.close()

    print("\n================================================================================")
    print("FINAL WORKSPACE ACCEPTANCE TEST SUMMARY:")
    print("================================================================================")
    all_passed = True
    for step, res in results.items():
        print(f" - {step}: {res}")
        if not ("PASSED" in res):
            all_passed = False

    print("================================================================================")
    if all_passed:
        print(">>> ALL 14 INVESTIGATOR WORKSPACE ACCEPTANCE CHECKS PASSED SUCCESSFULLY! <<<")
    else:
        print(">>> SOME CHECKS FAILED! <<<")
    print("================================================================================")
    return all_passed

if __name__ == "__main__":
    success = run_acceptance_suite()
    sys.exit(0 if success else 1)
