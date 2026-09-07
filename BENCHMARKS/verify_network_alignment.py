import time
from playwright.sync_api import sync_playwright

def capture_network_alignment():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1600, "height": 1000})
        page = context.new_page()

        # Login
        page.goto("http://127.0.0.1:8000/workspace")
        page.wait_for_selector("#login-username", timeout=8000)
        page.fill("#login-username", "officer1")
        page.fill("#login-password", "OfficerPass123!")
        page.click("#btn-login")
        page.wait_for_selector("#login-overlay", state="hidden", timeout=8000)
        time.sleep(1.0)

        # Open Network tab
        page.click("#tab-btn-network")
        page.wait_for_selector("#view-network.active", timeout=5000)
        time.sleep(1.0)

        # Switch to Demo Mode to inspect the multi-node concentric graph
        page.click("#btn-toggle-demo")
        time.sleep(1.5)

        # Capture Demo Network screenshot
        page.screenshot(path="BENCHMARKS/screenshots/crime_contact_network_concentric_aligned.png")
        print("[SCREENSHOT] Saved BENCHMARKS/screenshots/crime_contact_network_concentric_aligned.png")

        # Extract positions of anchor node, reticle, and SVG center
        metrics = page.evaluate("""() => {
            const anchor = cy.$('#CAN-PER-0001');
            const pos = anchor.position();
            const renderedPos = anchor.renderedPosition();
            const reticle = document.querySelector('#reticle-circle');
            const reticleCenter = {
                cx: reticle ? reticle.getAttribute('cx') : null,
                cy: reticle ? reticle.getAttribute('cy') : null
            };
            const pan = cy.pan();
            const zoom = cy.zoom();
            
            // Collect positions of nodes across layers
            const nodes = cy.nodes().map(n => ({
                id: n.id(),
                name: n.data('name'),
                layer: n.data('layer'),
                pos: n.position(),
                renderedPos: n.renderedPosition(),
                distFromCenter: Math.sqrt(Math.pow(n.position().x - pos.x, 2) + Math.pow(n.position().y - pos.y, 2))
            }));

            return {
                anchorPos: pos,
                anchorRenderedPos: renderedPos,
                reticleCenter: reticleCenter,
                pan: pan,
                zoom: zoom,
                nodes: nodes
            };
        }""")

        print(f"Metrics: Anchor pos = {metrics['anchorPos']}, Reticle center = {metrics['reticleCenter']}")
        for n in metrics['nodes']:
            print(f"Node {n['id']} ({n['name']}) Layer {n['layer']}: dist = {n['distFromCenter']:.2f}")

        # Also capture focused element screenshot
        network_el = page.query_selector("#cy-container")
        if network_el:
            network_el.screenshot(path="BENCHMARKS/screenshots/cy_container_cropped.png")
            print("[SCREENSHOT] Saved BENCHMARKS/screenshots/cy_container_cropped.png")

        browser.close()

if __name__ == "__main__":
    capture_network_alignment()
