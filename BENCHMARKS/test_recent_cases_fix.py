import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

WORKSPACE_ROOT = Path(r"D:\Proto SIH")
SCREENSHOT_DIR = WORKSPACE_ROOT / "BENCHMARKS" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

print("=" * 80)
print("VERIFYING RECENT CASES FIX (VISITED ONLY + MEMORY PROTECTION)")
print("=" * 80)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    context = browser.new_context(viewport={"width": 1600, "height": 960})
    page = context.new_page()

    # Step 1: Open workspace and clear localStorage
    page.goto("http://127.0.0.1:8000/workspace")
    page.evaluate("() => localStorage.clear()")
    page.reload()
    page.wait_for_selector("#login-username", timeout=10000)

    # Step 2: Login as officer1
    page.fill("#login-username", "officer1")
    page.fill("#login-password", "OfficerPass123!")
    page.click("button[type='submit']")
    page.wait_for_selector("#login-overlay", state="hidden", timeout=10000)
    time.sleep(1.0)

    # Step 3: Check Recent Cases on Portal - should show the clean empty state
    page.wait_for_selector("#portal-recent-list", timeout=5000)
    recent_text = page.inner_text("#portal-recent-list")
    print("[CHECK 1] Initial Recent Cases on Portal:")
    print(f"  Text: {recent_text.strip()[:80]}...")
    assert "No recently visited cases recorded" in recent_text, "Expected empty recent cases initially"
    page.screenshot(path=str(SCREENSHOT_DIR / "recent_cases_01_empty.png"))
    print("  -> PASSED: Clean empty state verified. None of the extra unvisited cases are shown.")

    # Step 4: Open 'Open Existing Case' modal
    page.click(".btn-open-existing-case")
    page.wait_for_selector("#modal-all-cases", state="visible", timeout=5000)
    time.sleep(0.5)

    # Step 5: Click 'Open Case' on CASE-2026-29F0
    open_btn = page.locator("#tbody-all-cases tr", has_text="CASE-2026-29F0").locator("button").first
    if open_btn.count() == 0:
        open_btn = page.locator("#tbody-all-cases button").first
    
    open_btn.click()
    page.wait_for_timeout(1500)

    active_id = page.inner_text("#case-detail-id")
    print(f"[CHECK 2] Entered workspace with case: {active_id}")
    assert active_id, "Expected valid active case ID"

    # Step 6: Return to Case Portal (click Home in activity bar)
    page.click("#activity-btn-home")
    page.wait_for_timeout(1000)

    # Step 7: Verify that under RECENT CASES, ONLY the visited case appears!
    rows = page.locator(".portal-case-row")
    row_count = rows.count()
    print(f"[CHECK 3] Portal recent cases row count: {row_count}")
    assert row_count == 1, f"Expected exactly 1 recent case row, but found {row_count}"

    row_id = rows.first.locator(".portal-case-id").inner_text()
    print(f"  Recent case row ID: {row_id}")
    assert active_id in row_id, f"Expected {active_id} in {row_id}"
    page.screenshot(path=str(SCREENSHOT_DIR / "recent_cases_02_only_visited.png"))
    print("  -> PASSED: Only the visited case is displayed in Recent Cases! None are extra.")

    # Step 8: Verify Clear Recent functionality
    clear_btn = page.locator("#portal-clear-recent-btn")
    assert clear_btn.is_visible(), "Clear Recent button must be visible when cases exist"
    clear_btn.click()
    page.wait_for_timeout(500)

    cleared_text = page.inner_text("#portal-recent-list")
    print("[CHECK 4] After clicking Clear Recent:")
    print(f"  Text: {cleared_text.strip()[:80]}...")
    assert "No recently visited cases recorded" in cleared_text, "Expected empty recent cases after clear"
    page.screenshot(path=str(SCREENSHOT_DIR / "recent_cases_03_cleared.png"))
    print("  -> PASSED: Clear Recent restored clean empty state.")

    browser.close()
    print("\n" + "=" * 80)
    print("ALL CHECKS PASSED: Visited-only tracking + leak prevention verified!")
    print("=" * 80)
