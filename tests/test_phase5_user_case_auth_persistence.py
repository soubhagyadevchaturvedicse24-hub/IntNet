"""
Targeted tests for Phase 5: Persistent User-Case Authorization across restarts.
Verifies that case authorizations survive process restarts and revocations persist.
"""

import pytest
from src.auth.models import TokenPayload, UserRole
from src.auth.service import AuthService
from src.cases.models import CaseCreate
from src.cases.service import CaseService


def test_user_case_authorization_persistence_across_restart(tmp_path):
    """
    Verifies that creating a case persists user authorization so that
    a fresh AuthService instance retains access after simulated reboot.
    """
    db_path = str(tmp_path / "test_user_auth_cases.db")

    from src.cases.repository import SQLiteCaseRepository
    auth1 = AuthService()
    auth1.db_path = db_path
    repo1 = SQLiteCaseRepository(db_path=db_path)
    case_service1 = CaseService(repository=repo1, auth_service=auth1)

    actor1 = TokenPayload(
        sub="USER-OFFICER-001",
        username="officer1",
        role=UserRole.INVESTIGATION_OFFICER,
        exp=9999999999,
        jti="test-jti-u1"
    )

    req = CaseCreate(
        case_name="Persistence Test Operation",
        description="Testing auth survival across restart"
    )
    new_case = case_service1.create_case(actor1, req)
    created_id = new_case.case_id

    # Verify officer1 has the case in instance 1
    user1 = auth1.get_user_by_id("USER-OFFICER-001")
    assert created_id in user1.authorized_case_ids

    # Instance 2: Fresh AuthService instance (simulating server restart)
    auth2 = AuthService()
    auth2.db_path = db_path

    user2 = auth2.get_user_by_id("USER-OFFICER-001")
    assert user2 is not None
    assert created_id in user2.authorized_case_ids, f"Expected {created_id} in {user2.authorized_case_ids}"

    # Now delete the case using instance 1
    boss_actor = TokenPayload(
        sub="USER-BOSS-001",
        username="boss1",
        role=UserRole.HIGHER_AUTHORITY,
        exp=9999999999,
        jti="test-jti-boss"
    )
    case_service1.delete_case(boss_actor, created_id)

    # Verify instance 1 user no longer has the case
    user1_after = auth1.get_user_by_id("USER-OFFICER-001")
    assert created_id not in user1_after.authorized_case_ids

    # Instance 3: Another fresh AuthService instance after deletion
    auth3 = AuthService()
    auth3.db_path = db_path
    user3 = auth3.get_user_by_id("USER-OFFICER-001")
    assert created_id not in user3.authorized_case_ids
