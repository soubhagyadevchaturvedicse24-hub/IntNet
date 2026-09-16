"""
Targeted tests for Phase 6: Logout and Session State Cleanup.
Verifies that workspace.html includes proper session, localStorage, and active case teardown.
"""

from pathlib import Path


def test_workspace_html_logout_cleanup():
    """
    Verifies that workspace.html explicitly cleans up active case identifiers
    and visited cases on handleLogout.
    """
    html_path = Path("src/api/workspace.html")
    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8")

    # Verify handleLogout clears crimenet_active_case_id from both storages
    assert "function handleLogout()" in content
    assert "sessionStorage.removeItem('crimenet_active_case_id');" in content
    assert "localStorage.removeItem('crimenet_active_case_id');" in content
    assert "localStorage.removeItem(RECENT_VISITED_STORAGE_KEY);" in content
    assert "activeCaseId = null;" in content

    # Verify loadCases prunes unauthorized stored case IDs
    assert "!currentCases.some(c => c.case_id === storedActiveId)" in content
