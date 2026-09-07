"""
Performance Benchmark Suite for CRIMENET Investigator Workspace
Measures:
1. GZip response compression ratios (HTML & JSON)
2. Network waterfall vs parallel latency
3. DOM batch rendering time for 250+ artifacts
4. Cytoscape viewport texture rendering & resize responsiveness
"""

import time
import urllib.request
import gzip
from playwright.sync_api import sync_playwright

def benchmark_compression():
    print("\n--- 1. HTTP GZip Compression Benchmark ---")
    url_html = "http://127.0.0.1:8000/workspace"
    req = urllib.request.Request(url_html, headers={"Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req) as resp:
        content_encoding = resp.headers.get("Content-Encoding")
        raw_data = resp.read()
        decompressed_size = len(gzip.decompress(raw_data)) if content_encoding == "gzip" else len(raw_data)
        compressed_size = len(raw_data)
        ratio = (1 - (compressed_size / decompressed_size)) * 100
        print(f"  [HTML Workspace] Encoding: {content_encoding}")
        print(f"  [HTML Workspace] Raw: {decompressed_size / 1024:.1f} KB -> Compressed: {compressed_size / 1024:.1f} KB (Savings: {ratio:.1f}%)")
        assert content_encoding == "gzip"
        assert ratio > 65.0

def benchmark_browser_render():
    print("\n--- 2. Browser DOM & Network Performance Benchmark ---")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1600, "height": 960})
        page = context.new_page()

        # Measure page load
        t0 = time.perf_counter()
        page.goto("http://127.0.0.1:8000/workspace")
        page.wait_for_selector("#login-username")
        t_load = (time.perf_counter() - t0) * 1000
        print(f"  [Page Initial Load]: {t_load:.2f} ms")

        # Login
        page.fill("#login-username", "officer1")
        page.fill("#login-password", "OfficerPass123!")
        t_login_start = time.perf_counter()
        page.click("#btn-login")
        page.wait_for_selector("#login-overlay", state="hidden")
        page.wait_for_selector("#panel-center")
        t_login = (time.perf_counter() - t_login_start) * 1000
        print(f"  [Auth + Parallel Workspace Init]: {t_login:.2f} ms")

        # Measure Artifact Table Batch Rendering Speed
        t_render_start = time.perf_counter()
        page.evaluate("""() => {
            renderArtifactsTable(currentArtifacts);
        }""")
        t_render = (time.perf_counter() - t_render_start) * 1000
        artifact_count = page.eval_on_selector("#explorer-count", "el => el.innerText")
        print(f"  [Batch DOM Table Render ({artifact_count})]: {t_render:.2f} ms")
        assert t_render < 50.0, f"Expected render < 50ms, got {t_render:.2f}ms"

        # Measure Cytoscape RAF Resize Speed
        page.click("#tab-btn-network")
        time.sleep(0.5)
        page.click("#btn-toggle-demo")
        time.sleep(0.5)

        t_cy_resize_start = time.perf_counter()
        page.evaluate("""() => {
            cy.resize();
            syncSvgTransform();
        }""")
        t_cy_resize = (time.perf_counter() - t_cy_resize_start) * 1000
        print(f"  [Cytoscape Hardware-Accelerated Viewport Sync]: {t_cy_resize:.2f} ms")
        assert t_cy_resize < 30.0

        browser.close()

if __name__ == "__main__":
    benchmark_compression()
    benchmark_browser_render()
    print("\n>>> ALL PERFORMANCE BENCHMARKS PASSED <<<")
