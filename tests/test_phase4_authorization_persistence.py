"""
Targeted tests for Phase 4: Persistent Case/Resource Authorization after restart.
Verifies that resource-to-case bindings survive process restarts via SQLite persistence.
"""

import pytest
from src.auth.models import TokenPayload, UserRole
from src.authorization.policy_engine import PolicyEngine, AuthorizationRequest


def test_resource_case_map_persistence_across_restart(tmp_path):
    """
    Verifies that resource_case_bindings persisted to SQLite are loaded
    into a fresh PolicyEngine instance after simulated server restart.
    """
    db_path = str(tmp_path / "test_auth_cases.db")

    # Instance 1: Register evidence and entity
    engine1 = PolicyEngine(db_path=db_path)
    engine1.register_resource_case("EV-2026-RESTART-001", "CASE-2026-001", "evidence")
    engine1.register_resource_case("CAN-PER-RESTART-002", "CASE-2026-001", "entity")

    assert engine1.resource_case_map["EV-2026-RESTART-001"] == "CASE-2026-001"
    assert engine1.resource_case_map["CAN-PER-RESTART-002"] == "CASE-2026-001"

    # Instance 2: Fresh instance (simulating server reboot)
    engine2 = PolicyEngine(db_path=db_path)

    # Must have restored the persisted bindings from SQLite
    assert "EV-2026-RESTART-001" in engine2.resource_case_map
    assert engine2.resource_case_map["EV-2026-RESTART-001"] == "CASE-2026-001"
    assert "CAN-PER-RESTART-002" in engine2.resource_case_map
    assert engine2.resource_case_map["CAN-PER-RESTART-002"] == "CASE-2026-001"

    # Verify ID manipulation defense on the restored instance
    actor = TokenPayload(
        sub="USER-OFFICER-002",
        username="officer2",
        role=UserRole.INVESTIGATION_OFFICER,
        exp=9999999999,
        jti="test-jti-restart"
    )

    req = AuthorizationRequest(
        actor=actor,
        action="READ_EVIDENCE",
        resource_type="evidence",
        resource_id="EV-2026-RESTART-001",
        target_case_id="CASE-2026-002"  # Mismatched target case
    )

    decision = engine2.evaluate(req, user_authorized_cases=["CASE-2026-002"])
    assert not decision.allowed
    assert "ID MANIPULATION DENY" in decision.reason
