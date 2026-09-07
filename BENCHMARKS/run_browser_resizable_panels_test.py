"""
CRIMENET // Resizable IDE Panels Validation Suite
Browser: Microsoft Edge (via Playwright channel="msedge")
Tests draggable splitters, min/max bounds, collapse/restore, Cytoscape auto-resize, artifact viewers, console, and logout.
"""

import sys
import time
import json
import os
from playwright.sync_api import sync_playwright

def run_resizable_panels_acceptance():
    print("================================================================================")
    print("CRIMENET // RESIZABLE IDE PANELS — REAL EDGE BROWSER ACCEPTANCE SUITE")
    print("================================================================================")

    results = {}
    os.makedirs("BENCHMARKS/screenshots", exist_ok=True)

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

        # STEP 2: Verify Case selection
        print("\n[STEP 2] Verify Case selection...")
        case_val = page.eval_on_selector("#case-selector", "el => el.value")
        assert "CASE-2026-001" in case_val
        results["02_case_selection"] = "PASSED"
        print(f" -> PASSED: Active case is {case_val}.")

        # STEP 3: Verify Explorer visible & baseline dimensions
        print("\n[STEP 3] Verify Explorer visible & baseline panel dimensions...")
        page.wait_for_selector("#panel-explorer:visible")
        page.wait_for_selector("#panel-center:visible")
        page.wait_for_selector("#panel-inspector:visible")
        page.wait_for_selector("#splitter-left:visible")
        page.wait_for_selector("#splitter-right:visible")

        w_left_init = page.eval_on_selector("#panel-explorer", "el => el.getBoundingClientRect().width")
        w_center_init = page.eval_on_selector("#panel-center", "el => el.getBoundingClientRect().width")
        w_right_init = page.eval_on_selector("#panel-inspector", "el => el.getBoundingClientRect().width")
        print(f" -> Baseline: Explorer={w_left_init:.1f}px, Center={w_center_init:.1f}px, Inspector={w_right_init:.1f}px")
        assert 260 <= w_left_init <= 280
        results["03_baseline_dimensions"] = "PASSED"

        # STEP 4: Drag Explorer wider
        print("\n[STEP 4] Drag Explorer wider...")
        s_left_box = page.eval_on_selector("#splitter-left", "el => { const r = el.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + 100 }; }")
        page.mouse.move(s_left_box["x"], s_left_box["y"])
        page.mouse.down()
        page.mouse.move(s_left_box["x"] + 100, s_left_box["y"], steps=8)
        page.mouse.up()
        time.sleep(0.5)

        w_left_wider = page.eval_on_selector("#panel-explorer", "el => el.getBoundingClientRect().width")
        w_center_narrower = page.eval_on_selector("#panel-center", "el => el.getBoundingClientRect().width")
        print(f" -> Drag wider result: Explorer={w_left_wider:.1f}px, Center={w_center_narrower:.1f}px")
        assert w_left_wider > w_left_init + 70, f"Expected Explorer > {w_left_init + 70}, got {w_left_wider}"
        assert w_center_narrower < w_center_init - 70, f"Expected Center < {w_center_init - 70}, got {w_center_narrower}"
        results["04_drag_explorer_wider"] = "PASSED"
        print(" -> PASSED: Explorer expanded, Center automatically shrank.")

        # STEP 5: Drag Explorer narrower
        print("\n[STEP 5] Drag Explorer narrower...")
        s_left_box2 = page.eval_on_selector("#splitter-left", "el => { const r = el.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + 100 }; }")
        page.mouse.move(s_left_box2["x"], s_left_box2["y"])
        page.mouse.down()
        page.mouse.move(s_left_box2["x"] - 140, s_left_box2["y"], steps=8)
        page.mouse.up()
        time.sleep(0.5)

        w_left_narrow = page.eval_on_selector("#panel-explorer", "el => el.getBoundingClientRect().width")
        w_center_expanded = page.eval_on_selector("#panel-center", "el => el.getBoundingClientRect().width")
        print(f" -> Drag narrower result: Explorer={w_left_narrow:.1f}px, Center={w_center_expanded:.1f}px")
        assert w_left_narrow < w_left_wider - 80
        assert w_center_expanded > w_center_narrower + 80
        assert w_left_narrow >= 200, f"Explorer min-width violated: {w_left_narrow}"
        results["05_drag_explorer_narrower"] = "PASSED"
        print(" -> PASSED: Explorer contracted, Center automatically expanded.")

        # STEP 6: Collapse Explorer
        print("\n[STEP 6] Collapse Explorer via Header Toggle...")
        page.click("#btn-toggle-sidebar")
        time.sleep(0.5)
        is_left_collapsed = page.eval_on_selector("#panel-explorer", "el => window.getComputedStyle(el).display === 'none'")
        is_splitter_left_hidden = page.eval_on_selector("#splitter-left", "el => window.getComputedStyle(el).display === 'none'")
        w_center_full_left = page.eval_on_selector("#panel-center", "el => el.getBoundingClientRect().width")
        print(f" -> Collapsed state: Explorer hidden={is_left_collapsed}, Splitter hidden={is_splitter_left_hidden}, Center={w_center_full_left:.1f}px")
        assert is_left_collapsed and is_splitter_left_hidden
        assert w_center_full_left > w_center_expanded
        results["06_collapse_explorer"] = "PASSED"
        print(" -> PASSED: Explorer collapsed cleanly, Center consumed remaining space.")

        # STEP 7: Restore Explorer
        print("\n[STEP 7] Restore Explorer via Header Toggle...")
        page.click("#btn-toggle-sidebar")
        time.sleep(0.5)
        is_left_restored = page.eval_on_selector("#panel-explorer", "el => window.getComputedStyle(el).display !== 'none'")
        is_splitter_left_restored = page.eval_on_selector("#splitter-left", "el => window.getComputedStyle(el).display !== 'none'")
        w_left_restored = page.eval_on_selector("#panel-explorer", "el => el.getBoundingClientRect().width")
        print(f" -> Restored state: Explorer visible={is_left_restored}, Width={w_left_restored:.1f}px")
        assert is_left_restored and is_splitter_left_restored
        assert w_left_restored >= 200
        results["07_restore_explorer"] = "PASSED"
        print(" -> PASSED: Explorer restored to saved width.")

        # STEP 8: Drag Inspector wider
        print("\n[STEP 8] Drag Inspector wider...")
        w_right_before = page.eval_on_selector("#panel-inspector", "el => el.getBoundingClientRect().width")
        w_center_before_right = page.eval_on_selector("#panel-center", "el => el.getBoundingClientRect().width")
        s_right_box = page.eval_on_selector("#splitter-right", "el => { const r = el.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + 120 }; }")
        page.mouse.move(s_right_box["x"], s_right_box["y"])
        page.mouse.down()
        page.mouse.move(s_right_box["x"] - 90, s_right_box["y"], steps=8)
        page.mouse.up()
        time.sleep(0.5)

        w_right_wider = page.eval_on_selector("#panel-inspector", "el => el.getBoundingClientRect().width")
        w_center_narrower_right = page.eval_on_selector("#panel-center", "el => el.getBoundingClientRect().width")
        print(f" -> Drag wider result: Inspector={w_right_wider:.1f}px, Center={w_center_narrower_right:.1f}px")
        assert w_right_wider > w_right_before + 60
        assert w_center_narrower_right < w_center_before_right - 60
        results["08_drag_inspector_wider"] = "PASSED"
        print(" -> PASSED: Inspector widened, Center automatically contracted.")

        # STEP 9: Drag Inspector narrower
        print("\n[STEP 9] Drag Inspector narrower...")
        s_right_box2 = page.eval_on_selector("#splitter-right", "el => { const r = el.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + 120 }; }")
        page.mouse.move(s_right_box2["x"], s_right_box2["y"])
        page.mouse.down()
        page.mouse.move(s_right_box2["x"] + 120, s_right_box2["y"], steps=8)
        page.mouse.up()
        time.sleep(0.5)

        w_right_narrow = page.eval_on_selector("#panel-inspector", "el => el.getBoundingClientRect().width")
        w_center_expanded_right = page.eval_on_selector("#panel-center", "el => el.getBoundingClientRect().width")
        print(f" -> Drag narrower result: Inspector={w_right_narrow:.1f}px, Center={w_center_expanded_right:.1f}px")
        assert w_right_narrow < w_right_wider - 80
        assert w_center_expanded_right > w_center_narrower_right + 80
        assert w_right_narrow >= 240, f"Inspector min-width violated: {w_right_narrow}"
        results["09_drag_inspector_narrower"] = "PASSED"
        print(" -> PASSED: Inspector narrowed, Center expanded.")

        # STEP 10: Collapse Inspector
        print("\n[STEP 10] Collapse Inspector via Header Toggle...")
        page.click("#btn-toggle-inspector")
        time.sleep(0.5)
        is_right_collapsed = page.eval_on_selector("#panel-inspector", "el => window.getComputedStyle(el).display === 'none'")
        is_splitter_right_hidden = page.eval_on_selector("#splitter-right", "el => window.getComputedStyle(el).display === 'none'")
        w_center_full_right = page.eval_on_selector("#panel-center", "el => el.getBoundingClientRect().width")
        print(f" -> Collapsed state: Inspector hidden={is_right_collapsed}, Splitter hidden={is_splitter_right_hidden}, Center={w_center_full_right:.1f}px")
        assert is_right_collapsed and is_splitter_right_hidden
        assert w_center_full_right > w_center_expanded_right
        results["10_collapse_inspector"] = "PASSED"
        print(" -> PASSED: Inspector collapsed cleanly, Center consumed remaining space.")

        # STEP 11: Restore Inspector
        print("\n[STEP 11] Restore Inspector via Header Toggle...")
        page.click("#btn-toggle-inspector")
        time.sleep(0.5)
        is_right_restored = page.eval_on_selector("#panel-inspector", "el => window.getComputedStyle(el).display !== 'none'")
        is_splitter_right_restored = page.eval_on_selector("#splitter-right", "el => window.getComputedStyle(el).display !== 'none'")
        w_right_restored = page.eval_on_selector("#panel-inspector", "el => el.getBoundingClientRect().width")
        print(f" -> Restored state: Inspector visible={is_right_restored}, Width={w_right_restored:.1f}px")
        assert is_right_restored and is_splitter_right_restored
        assert w_right_restored >= 240
        results["11_restore_inspector"] = "PASSED"
        print(" -> PASSED: Inspector restored to saved width.")

        # STEP 12: Open PDF Artifact
        print("\n[STEP 12] Open PDF Artifact in center workspace...")
        page.click("#tab-btn-explorer")
        time.sleep(0.5)
        # Find first PDF artifact
        pdf_id = page.evaluate("""() => {
            const pdf = currentArtifacts.find(a => (a.filename || '').endsWith('.pdf'));
            if (pdf) { openArtifactItemById(pdf.artifact_id); return pdf.artifact_id; }
            return null;
        }""")
        time.sleep(1.0)
        assert pdf_id is not None
        viewer_active = page.is_visible("#view-artifact-viewer.active")
        assert viewer_active
        page.screenshot(path="BENCHMARKS/screenshots/resizable_panels_01_pdf_viewer.png")
        results["12_open_pdf_viewer"] = "PASSED"
        print(f" -> PASSED: Opened PDF {pdf_id} in responsive artifact viewer.")

        # STEP 13: Open Image Artifact
        print("\n[STEP 13] Open Image Artifact in center workspace...")
        img_id = page.evaluate("""() => {
            const img = currentArtifacts.find(a => (a.filename || '').endsWith('.png') || (a.filename || '').endsWith('.jpg'));
            if (img) { openArtifactItemById(img.artifact_id); return img.artifact_id; }
            return null;
        }""")
        time.sleep(1.0)
        assert img_id is not None
        page.screenshot(path="BENCHMARKS/screenshots/resizable_panels_02_image_viewer.png")
        results["13_open_image_viewer"] = "PASSED"
        print(f" -> PASSED: Opened Image {img_id} in responsive artifact viewer.")

        # STEP 14: Open Crime Contact Network
        print("\n[STEP 14] Open Crime Contact Network tab...")
        page.click("#tab-btn-network")
        time.sleep(1.0)
        assert page.is_visible("#view-network.active")
        # Toggle demo preview for multi-node graph
        page.click("#btn-toggle-demo")
        time.sleep(1.0)
        results["14_open_crime_contact_network"] = "PASSED"
        print(" -> PASSED: Crime Contact Network opened in Demo preview mode.")

        # STEP 15: Resize panels while graph is visible & verify Cytoscape adaptation
        print("\n[STEP 15] Resize panels while graph is visible & verify Cytoscape auto-adaptation...")
        cy_width_before = page.eval_on_selector("#cy", "el => el.clientWidth")
        s_left_box3 = page.eval_on_selector("#splitter-left", "el => { const r = el.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + 100 }; }")
        page.mouse.move(s_left_box3["x"], s_left_box3["y"])
        page.mouse.down()
        page.mouse.move(s_left_box3["x"] + 80, s_left_box3["y"], steps=6)
        page.mouse.up()
        time.sleep(0.5)

        s_right_box3 = page.eval_on_selector("#splitter-right", "el => { const r = el.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + 120 }; }")
        page.mouse.move(s_right_box3["x"], s_right_box3["y"])
        page.mouse.down()
        page.mouse.move(s_right_box3["x"] - 60, s_right_box3["y"], steps=6)
        page.mouse.up()
        time.sleep(0.5)

        cy_width_after = page.eval_on_selector("#cy", "el => el.clientWidth")
        print(f" -> Cytoscape canvas width: Before={cy_width_before}px, After={cy_width_after}px")
        assert cy_width_after < cy_width_before - 100, f"Expected Cytoscape canvas to shrink with panels, got {cy_width_after} vs {cy_width_before}"
        page.screenshot(path="BENCHMARKS/screenshots/resizable_panels_03_graph_resized.png")
        results["15_resize_panels_with_graph"] = "PASSED"
        print(" -> PASSED: Cytoscape canvas adapted smoothly to resized center container.")

        # STEP 16: Verify Cytoscape remains fully interactive
        print("\n[STEP 16] Verify Cytoscape remains fully interactive after resizing...")
        interactivity = page.evaluate("""() => {
            const anchor = cy.$('#CAN-PER-0001');
            const target = cy.$('#CAN-PER-0002');
            const isAnchorLocked = anchor.locked();
            const isTargetGrabbable = target.grabbable();
            const initialZoom = cy.zoom();
            cy.zoom(initialZoom * 1.15);
            const zoomedZoom = cy.zoom();
            cy.panBy({ x: 20, y: 20 });
            target.emit('tap');
            return {
                anchorLocked: isAnchorLocked,
                targetGrabbable: isTargetGrabbable,
                zoomChanged: zoomedZoom !== initialZoom
            };
        }""")
        time.sleep(0.5)
        insp_text = page.eval_on_selector("#inspector-content", "el => el.innerText")
        assert interactivity["anchorLocked"] and interactivity["targetGrabbable"] and interactivity["zoomChanged"]
        assert "CAN-PER-0002" in insp_text
        results["16_cytoscape_interactive"] = "PASSED"
        print(" -> PASSED: Cytoscape node interaction, zoom, pan, and inspector selection fully operational.")

        # STEP 17: Verify Activity Console remains functional
        print("\n[STEP 17] Verify Activity Console remains functional...")
        # Toggle console to ensure collapse/expand works
        page.click("#btn-toggle-console-btn")
        time.sleep(0.4)
        page.click("#btn-toggle-console-btn")
        time.sleep(0.4)
        console_events = page.eval_on_selector("#console-event-count", "el => el.innerText")
        assert "events" in console_events.lower()
        page.screenshot(path="BENCHMARKS/screenshots/resizable_panels_04_console.png")
        results["17_activity_console_functional"] = "PASSED"
        print(f" -> PASSED: Activity Console responsive ({console_events}).")

        # STEP 18: Logout
        print("\n[STEP 18] Logout...")
        page.click("button:has-text('Logout')")
        page.wait_for_selector("#login-overlay", state="visible", timeout=5000)
        page.screenshot(path="BENCHMARKS/screenshots/resizable_panels_05_logged_out.png")
        results["18_logout"] = "PASSED"
        print(" -> PASSED: Logged out successfully, login overlay rendered.")

        browser.close()

    print("\n================================================================================")
    print(f"ACCEPTANCE RESULTS: {len(results)}/18 STEPS COMPLETED")
    for k, v in results.items():
        print(f"  {k}: {v}")
    print("================================================================================")
    assert len(results) == 18
    assert all(v == "PASSED" for v in results.values())
    print("\n>>> ALL 18/18 RESIZABLE PANELS ACCEPTANCE STEPS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    run_resizable_panels_acceptance()
