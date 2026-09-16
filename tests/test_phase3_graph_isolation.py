"""
Targeted tests for Phase 3: Case-scoped Graph Isolation.
Verifies that entity/relationship queries for one case never expose another case's data.
"""

import pytest
from src.auth.models import TokenPayload, UserRole
from src.entity_resolution.service import EntityGraphService
from src.entity_resolution.graph_integrator import KuzuEntityGraphIntegrator
from src.authorization.policy_engine import PolicyEngine
from src.audit.service import AuditService
from src.auth.service import AuthService
from src.cases.service import CaseService


def test_cross_case_graph_isolation(tmp_path):
    """
    Verifies that entities and relationships ingested for Case A
    are completely invisible to Case B queries.
    """
    db_path = str(tmp_path / "kuzu_test_db")
    integrator = KuzuEntityGraphIntegrator(db_path=db_path)
    integrator.setup()

    policy_engine = PolicyEngine()
    audit_service = AuditService()
    auth_service = AuthService()
    case_service = CaseService(policy_engine=policy_engine, audit_service=audit_service, auth_service=auth_service)

    service = EntityGraphService(
        graph_integrator=integrator,
        case_service=case_service,
        policy_engine=policy_engine,
        audit_service=audit_service,
        auth_service=auth_service
    )

    actor1 = TokenPayload(sub="USER-OFFICER-001", username="officer1", role=UserRole.INVESTIGATION_OFFICER, exp=9999999999, jti="test-jti-1")
    actor2 = TokenPayload(sub="USER-OFFICER-002", username="officer2", role=UserRole.INVESTIGATION_OFFICER, exp=9999999999, jti="test-jti-2")

    # Ingest entity for CASE-2026-001
    ent_a = {"canonical_entity_id": "CAN-TEST-A1", "entity_type": "Person", "canonical_name": "Target Alpha", "supporting_observations_count": 2}
    integrator.ingest_canonical_entities([ent_a])
    policy_engine.register_resource_case("CAN-TEST-A1", "CASE-2026-001")

    # Ingest entity for CASE-2026-002
    ent_b = {"canonical_entity_id": "CAN-TEST-B1", "entity_type": "Person", "canonical_name": "Target Beta", "supporting_observations_count": 3}
    integrator.ingest_canonical_entities([ent_b])
    policy_engine.register_resource_case("CAN-TEST-B1", "CASE-2026-002")

    # 1. Query Case 1 graph -> should only see Case 1 entities
    graph1 = service.get_case_graph(actor1, "CASE-2026-001", demo=False)
    node_ids1 = [n["id"] for n in graph1["nodes"]]
    assert "CAN-TEST-A1" in node_ids1
    assert "CAN-TEST-B1" not in node_ids1

    # 2. Query Case 2 graph -> should only see Case 2 entities
    graph2 = service.get_case_graph(actor2, "CASE-2026-002", demo=False)
    node_ids2 = [n["id"] for n in graph2["nodes"]]
    assert "CAN-TEST-B1" in node_ids2
    assert "CAN-TEST-A1" not in node_ids2

    # 3. Attempt to inspect CAN-TEST-A1 under CASE-2026-002 -> ID manipulation denial
    with pytest.raises(PermissionError) as exc:
        service.get_entity_details(actor2, "CASE-2026-002", "CAN-TEST-A1", demo=False)
    assert "ID MANIPULATION DENY" in str(exc.value)
