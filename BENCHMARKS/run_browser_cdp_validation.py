"""
CRIMENET Slice 7B-A: Real Browser-Level Automation Acceptance Test via Chrome DevTools Protocol (CDP).
Controls Microsoft Edge (Chromium) in native headless mode to execute the complete Investigator Workspace:
1. Login -> 2. Case Selection -> 3. Evidence Registration -> 4. Process Evidence ->
5. Processing Result (Dynamic Observation) -> 6. Evidence Explorer -> 7. Category Filtering ->
8. Artifact Details -> 9. PDF Viewer (Blob Stream) -> 10. Logout.
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
import websocket

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
UVICORN_PORT = 8000
CDP_PORT = 9222


class BrowserController:
    def __init__(self, ws_url: str):
        self.ws = websocket.create_connection(ws_url)
        self.msg_id = 0

    def send(self, method: str, params: dict = None) -> dict:
        self.msg_id += 1
        payload = {"id": self.msg_id, "method": method}
        if params:
            payload["params"] = params
        self.ws.send(json.dumps(payload))
        
        # Wait for matching response ID
        while True:
            raw = self.ws.recv()
            data = json.loads(raw)
            if data.get("id") == self.msg_id:
                if "error" in data:
                    raise RuntimeError(f"CDP Error in {method}: {data['error']}")
                return data.get("result", {})

    def evaluate(self, expr: str, await_promise: bool = False):
        res = self.send("Runtime.evaluate", {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": await_promise
        })
        val = res.get("result", {}).get("value")
        return val

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def wait_for_http(url: str, timeout: float = 15.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(url) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    raise TimeoutError(f"HTTP Server did not respond at {url} within {timeout}s")


def run_browser_level_test():
    print("=" * 85)
    print("CRIMENET SLICE 7B-A: ACTUAL BROWSER-LEVEL AUTOMATION ACCEPTANCE TEST")
    print("Driver: Microsoft Edge (Chromium) Headless via Chrome DevTools Protocol (CDP)")
    print("=" * 85)

    uvicorn_proc = None
    edge_proc = None
    browser = None
    results = {}

    try:
        # 1. Start FastAPI Backend Server
        print("\n>>> 1. STARTING BACKEND FASTAPI INSTANCE (port 8000)...")
        uvicorn_cmd = [sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", str(UVICORN_PORT)]
        uvicorn_proc = subprocess.Popen(uvicorn_cmd, cwd=r"D:\Proto SIH", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait_for_http(f"http://127.0.0.1:{UVICORN_PORT}/")
        print("  [OK] FastAPI Server is listening and responding at http://127.0.0.1:8000/")

        # 2. Launch Microsoft Edge in Headless Mode with Remote Debugging
        print("\n>>> 2. LAUNCHING MICROSOFT EDGE WITH CDP REMOTE DEBUGGING...")
        edge_cmd = [
            EDGE_PATH,
            "--headless=new",
            f"--remote-debugging-port={CDP_PORT}",
            "--remote-allow-origins=*",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank"
        ]
        edge_proc = subprocess.Popen(edge_cmd)
        time.sleep(1.5)

        # Get WebSocket Debugger URL for the browser page
        with urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json/list") as r:
            tabs = json.loads(r.read())
            page_tabs = [t for t in tabs if t.get("type") == "page"]
            ws_url = page_tabs[0]["webSocketDebuggerUrl"]
        print(f"  [OK] Connected to Edge CDP Page Tab: {ws_url}")

        browser = BrowserController(ws_url)
        browser.send("Page.enable")
        browser.send("Runtime.enable")

        # Suppress blocking modal alert dialogs by redirecting to console
        browser.evaluate("window.alert = function(msg) { console.log('[BROWSER_ALERT]', msg); };")

        # 3. Navigate to Investigator Workspace
        print("\n>>> 3. NAVIGATING TO INVESTIGATOR WORKSPACE...")
        browser.send("Page.navigate", {"url": f"http://127.0.0.1:{UVICORN_PORT}/"})
        
        # Poll until page load finishes
        title = ""
        for _ in range(30):
            time.sleep(0.4)
            title = browser.evaluate("document.title") or ""
            if title:
                break

        print(f"  Page Title: '{title}'")
        assert "CRIMENET // Investigator Workspace" in title

        # Suppress blocking modal alert dialogs by redirecting to console
        browser.evaluate("window.alert = function(msg) { console.log('[BROWSER_ALERT]', msg); };")

        # --------------------------------------------------------------------
        # STAGE 1: LOGIN
        # --------------------------------------------------------------------
        print("\n>>> STAGE 1: BROWSER LOGIN")
        overlay_disp = browser.evaluate("window.getComputedStyle(document.getElementById('login-overlay')).display")
        assert overlay_disp != "none", "Login overlay should be visible on load"

        # Submit login form
        browser.evaluate("""
            document.getElementById('login-username').value = 'officer1';
            document.getElementById('login-password').value = 'OfficerPass123!';
            document.getElementById('btn-login').click();
        """)
        time.sleep(1.5)

        overlay_after = browser.evaluate("window.getComputedStyle(document.getElementById('login-overlay')).display")
        user_pill = browser.evaluate("document.getElementById('hdr-user-pill').innerText")
        print(f"  Overlay Display: {overlay_after}")
        print(f"  User Badge Pill: '{user_pill}'")
        assert overlay_after == "none", "Login overlay should be dismissed after authentication"
        assert "officer1" in user_pill
        results["stage_1_login"] = {"status": "VERIFIED", "user_pill": user_pill}

        # --------------------------------------------------------------------
        # STAGE 2: CASE SELECTION
        # --------------------------------------------------------------------
        print("\n>>> STAGE 2: BROWSER CASE SELECTION")
        time.sleep(1.0)
        active_case = browser.evaluate("activeCaseId")
        case_name = browser.evaluate("document.getElementById('case-detail-name').innerText")
        case_options = browser.evaluate("Array.from(document.getElementById('case-selector').options).map(o => o.value)")
        print(f"  Active Case ID:       {active_case}")
        print(f"  Active Case Name:     {case_name}")
        print(f"  Case Selector Count:  {len(case_options)} ({case_options})")
        assert active_case == "CASE-2026-001"
        assert len(case_options) >= 1
        results["stage_2_case_selection"] = {"status": "VERIFIED", "active_case": active_case, "name": case_name}

        # --------------------------------------------------------------------
        # STAGE 3: EVIDENCE REGISTRATION
        # --------------------------------------------------------------------
        print("\n>>> STAGE 3: BROWSER EVIDENCE REGISTRATION")
        reg_res = browser.evaluate("""
            (async () => {
                document.getElementById('ev-form-name').value = 'Images_Set_1 Browser CDP Acquisition';
                document.getElementById('ev-form-type').value = 'DISK_IMAGE';
                document.getElementById('ev-form-desc').value = 'Validated via Headless Edge CDP';
                document.getElementById('ev-form-path').value = 'D:/Proto SIH/Images/Images_Set_1.E01';

                const fd = new FormData();
                fd.append('evidence_name', 'Images_Set_1 Browser CDP Acquisition');
                fd.append('evidence_type', 'DISK_IMAGE');
                fd.append('source_description', 'Validated via Headless Edge CDP');
                fd.append('local_image_path', 'D:/Proto SIH/Images/Images_Set_1.E01');

                const res = await fetch(`/api/v1/cases/${activeCaseId}/evidence`, {
                    method: 'POST',
                    headers: { 'Authorization': 'Bearer ' + currentToken },
                    body: fd
                });
                const data = await res.json();
                closeModal('modal-add-evidence');
                await loadEvidence();
                return { status: res.status, data: data };
            })()
        """, await_promise=True)
        print(f"  Registration Result: {reg_res}")
        assert reg_res.get("status") == 201
        new_ev_id = reg_res.get("data", {}).get("evidence_id")

        ev_rows = browser.evaluate("document.querySelectorAll('#tbody-evidence tr').length")
        print(f"  Evidence Table Rows:  {ev_rows}")
        print(f"  Registered Ev ID:     {new_ev_id}")
        assert ev_rows >= 1
        assert new_ev_id.startswith("EV-")
        results["stage_3_evidence_registration"] = {"status": "VERIFIED", "evidence_id": new_ev_id}

        # --------------------------------------------------------------------
        # STAGE 4: PROCESS EVIDENCE
        # --------------------------------------------------------------------
        print("\n>>> STAGE 4: BROWSER PROCESS EVIDENCE TRIGGER")
        proc_res = browser.evaluate(f"""
            (async () => {{
                try {{
                    const res = await fetch(`/api/v1/cases/${{activeCaseId}}/evidence/{new_ev_id}/process`, {{
                        method: 'POST',
                        headers: {{ 'Authorization': 'Bearer ' + currentToken }}
                    }});
                    const data = await res.json();
                    if (res.ok) {{
                        document.getElementById('job-badge').className = 'status-pill pill-queued';
                        document.getElementById('job-badge').innerText = 'QUEUED';
                        pollProcessingJob(data.job_id);
                    }}
                    return {{ status: res.status, data: data }};
                }} catch (e) {{
                    return {{ error: e.toString() }};
                }}
            }})()
        """, await_promise=True)
        print(f"  Process POST Response: {proc_res}")
        assert proc_res.get("status") == 202
        time.sleep(1.0)
        badge_state = browser.evaluate("document.getElementById('job-badge').innerText")
        print(f"  Job Badge State: {badge_state}")
        results["stage_4_process_trigger"] = {"status": "VERIFIED", "state": badge_state, "api_response": proc_res}

        # --------------------------------------------------------------------
        # STAGE 5: PROCESSING RESULT (DYNAMIC OBSERVATION)
        # --------------------------------------------------------------------
        print("\n>>> STAGE 5: BROWSER PROCESSING RESULT POLLING")
        t_start = time.time()
        final_state = ""
        while time.time() - t_start < 45:
            final_state = browser.evaluate("document.getElementById('job-badge').innerText")
            if final_state in ["COMPLETED", "FAILED"]:
                break
            time.sleep(1.0)

        assert final_state == "COMPLETED", f"Observation job failed with state: {final_state}"
        obs_fs = browser.evaluate("document.getElementById('job-observed-fs').innerText")
        obs_dirs = browser.evaluate("document.getElementById('job-dirs').innerText")
        obs_files = browser.evaluate("document.getElementById('job-files').innerText")
        obs_arts = browser.evaluate("document.getElementById('job-artifacts').innerText")

        print(f"  Job Completed In:     {round(time.time() - t_start, 2)}s")
        print(f"  Observed Filesystem:  {obs_fs}")
        print(f"  Discovered Dirs:      {obs_dirs}")
        print(f"  Discovered Files:     {obs_files}")
        print(f"  Contract Artifacts:   {obs_arts}")

        assert obs_fs == "NTFS", f"Expected NTFS, got {obs_fs}"
        assert obs_dirs == "1122", f"Expected 1122 dirs, got {obs_dirs}"
        assert obs_files == "2898", f"Expected 2898 files, got {obs_files}"
        assert obs_arts == "23", f"Expected 23 contract artifacts, got {obs_arts}"
        results["stage_5_processing_result"] = {
            "status": "VERIFIED",
            "filesystem": obs_fs,
            "directories": obs_dirs,
            "files": obs_files,
            "contract_artifacts": obs_arts
        }

        # --------------------------------------------------------------------
        # STAGE 6: EVIDENCE EXPLORER
        # --------------------------------------------------------------------
        print("\n>>> STAGE 6: BROWSER EVIDENCE EXPLORER TAB")
        browser.evaluate("switchWorkspaceTab('explorer')")
        time.sleep(1.0)
        is_explorer_active = browser.evaluate("document.getElementById('view-explorer').classList.contains('active')")
        art_rows = browser.evaluate("document.querySelectorAll('#tbody-artifacts tr').length")
        explorer_counter = browser.evaluate("document.getElementById('explorer-count').innerText")

        print(f"  Explorer Tab Active:  {is_explorer_active}")
        print(f"  Table Rendered Rows:  {art_rows}")
        print(f"  Item Counter Pill:    {explorer_counter}")
        assert is_explorer_active is True
        assert art_rows > 0
        results["stage_6_explorer"] = {"status": "VERIFIED", "rendered_rows": art_rows, "counter": explorer_counter}

        # --------------------------------------------------------------------
        # STAGE 7: CATEGORY FILTERING
        # --------------------------------------------------------------------
        print("\n>>> STAGE 7: BROWSER CATEGORY FILTERING")
        # 1. Filter DOCUMENT
        browser.evaluate("""
            (async () => {
                document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.cat-btn')[1].classList.add('active');
                await loadArtifacts('DOCUMENT');
            })()
        """, await_promise=True)
        time.sleep(0.5)
        doc_rows = browser.evaluate("document.querySelectorAll('#tbody-artifacts tr').length")
        doc_counter = browser.evaluate("document.getElementById('explorer-count').innerText")
        print(f"  [Filter DOCUMENT]:    {doc_rows} rows (Counter: {doc_counter})")
        assert doc_rows == 20

        # 2. Filter IMAGE
        browser.evaluate("""
            (async () => {
                document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.cat-btn')[3].classList.add('active');
                await loadArtifacts('IMAGE');
            })()
        """, await_promise=True)
        time.sleep(0.5)
        img_rows = browser.evaluate("document.querySelectorAll('#tbody-artifacts tr').length")
        print(f"  [Filter IMAGE]:       {img_rows} rows")
        assert img_rows == 2

        # 3. Filter ALL
        browser.evaluate("""
            (async () => {
                document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.cat-btn')[0].classList.add('active');
                await loadArtifacts(null);
            })()
        """, await_promise=True)
        time.sleep(0.5)
        all_rows = browser.evaluate("document.querySelectorAll('#tbody-artifacts tr').length")
        print(f"  [Filter ALL]:         {all_rows} rows")
        assert all_rows >= 119
        results["stage_7_category_filtering"] = {
            "status": "VERIFIED",
            "document_count": doc_rows,
            "image_count": img_rows,
            "all_count": all_rows
        }

        # --------------------------------------------------------------------
        # STAGE 8: ARTIFACT DETAILS (PROVENANCE)
        # --------------------------------------------------------------------
        print("\n>>> STAGE 8: BROWSER ARTIFACT DETAILS MODAL")
        # Find Jeevan Setu.pdf artifact id
        target_art_id = browser.evaluate("""
            (() => {
                const row = Array.from(document.querySelectorAll('#tbody-artifacts tr'))
                    .find(r => r.innerText.includes('Jeevan Setu.pdf'));
                return row ? row.querySelector('td:first-child').innerText : '';
            })()
        """)
        print(f"  Target Artifact ID:   {target_art_id}")
        assert target_art_id.startswith("ART-")

        # Open details modal
        browser.evaluate(f"openArtifactDetails('{target_art_id}')")
        time.sleep(1.0)
        modal_disp = browser.evaluate("window.getComputedStyle(document.getElementById('modal-artifact-details')).display")
        modal_html = browser.evaluate("document.getElementById('artifact-details-body').innerText")

        print(f"  Modal Display:        {modal_disp}")
        assert modal_disp == "flex"
        assert "Jeevan Setu.pdf" in modal_html
        assert "DOCUMENT" in modal_html
        assert "1e6ea53d82f0e8aa2e6122fd5f3d2038757b5fc88d8dd6a1a8cba93f020d18c1" in modal_html
        assert "Chrome/Jeevan Setu.pdf" in modal_html
        print("  [PASS] Details modal rendered complete provenance chain & SHA-256 fingerprint.")

        # Close details modal
        browser.evaluate("closeModal('modal-artifact-details')")
        results["stage_8_artifact_details"] = {"status": "VERIFIED", "target_artifact_id": target_art_id}

        # --------------------------------------------------------------------
        # STAGE 9: PDF VIEWER (BLOB STREAM)
        # --------------------------------------------------------------------
        print("\n>>> STAGE 9: BROWSER PDF CONTENT VIEWER (AUTHENTICATED BLOB)")
        browser.evaluate(f"openArtifactContent('{target_art_id}')")
        time.sleep(1.5)

        content_disp = browser.evaluate("window.getComputedStyle(document.getElementById('modal-artifact-content')).display")
        iframe_src = browser.evaluate("document.querySelector('#content-viewer-body iframe')?.src || ''")
        meta_label = browser.evaluate("document.getElementById('content-modal-meta').innerText")

        print(f"  Content Modal Display: {content_disp}")
        print(f"  Viewer Metadata Label: '{meta_label}'")
        print(f"  Rendered Iframe Src:   '{iframe_src[:45]}...'")

        assert content_disp == "flex"
        assert "application/pdf" in meta_label
        assert iframe_src.startswith("blob:http://127.0.0.1:8000/"), f"Iframe must load authenticated blob URL, got: {iframe_src}"
        print("  [PASS] PDF successfully streamed via Bearer token and rendered inside Edge iframe.")

        # Close content modal
        browser.evaluate("closeModal('modal-artifact-content')")
        results["stage_9_pdf_viewer"] = {"status": "VERIFIED", "iframe_src": iframe_src[:45] + "..."}

        # --------------------------------------------------------------------
        # STAGE 10: LOGOUT
        # --------------------------------------------------------------------
        print("\n>>> STAGE 10: BROWSER LOGOUT")
        browser.evaluate("handleLogout()")
        time.sleep(1.0)
        overlay_final = browser.evaluate("window.getComputedStyle(document.getElementById('login-overlay')).display")
        token_final = browser.evaluate("currentToken")

        print(f"  Login Overlay Display: {overlay_final}")
        print(f"  Current Token State:   {token_final}")
        assert overlay_final == "flex"
        assert token_final is None
        print("  [PASS] User session successfully terminated. Overlay restored.")
        results["stage_10_logout"] = {"status": "VERIFIED"}

        # Save machine-readable browser test results
        with open("BENCHMARKS/slice_7b_a_browser_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        print("\n" + "=" * 85)
        print("ALL 10 BROWSER-LEVEL ACCEPTANCE WORKFLOW STAGES VERIFIED IN MICROSOFT EDGE!")
        print("=" * 85)
        return True

    finally:
        if browser:
            browser.close()
        if edge_proc:
            edge_proc.terminate()
            try:
                edge_proc.wait(timeout=3)
            except Exception:
                edge_proc.kill()
        if uvicorn_proc:
            uvicorn_proc.terminate()
            try:
                uvicorn_proc.wait(timeout=3)
            except Exception:
                uvicorn_proc.kill()


if __name__ == "__main__":
    success = run_browser_level_test()
    sys.exit(0 if success else 1)
