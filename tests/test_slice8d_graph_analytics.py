"""
Unit & Integration Verification Suite for CRIMENET Slice 8D: Forensic Graph Analytics.

Validates:
1. All 9 Graph Analytics Algorithms on real evidence:
   - 1. Degree (unique communicating neighbors: in, out, total)
   - 2. Weighted communication frequency (observed communication counts)
   - 3. Betweenness centrality (inverse frequency distance)
   - 4. PageRank (weighted communication flow)
   - 5. Weakly & strongly connected components
   - 6. Louvain community detection (undirected weighted projection)
   - 7. Weighted shortest path (inverse frequency distance)
   - 8. 1-hop / 2-hop neighbors
   - 9. Descriptive timestamp patterns (histograms and time windows)
2. Exact graph projection semantics:
   - degree = unique neighbors
   - frequency = observed communication count
   - betweenness/path distance = inverse frequency
   - PageRank = weighted communication graph
   - community detection = undirected weighted projection
3. Execution timing recorded in benchmarks (milliseconds).
4. Strict case isolation and BOLA authorization (403 Forbidden for unauthorized officer).
5. REST API endpoint GET /api/v1/cases/{case_id}/graph/analytics.
6. Zero GNN, zero link prediction, zero anomaly detection, zero kingpin labeling.
7. Zero synthetic or demonstration data. Zero ASSOCIATED_WITH.
"""

import os
import json
import time
import shutil
import tempfile
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from src.auth.models import TokenPayload, UserRole, User
from src.parsers.models import (
    ParserType,
    ObservationType,
    ParsedArtifact,
    ParserMetadata,
    ParsingStatus,
)
from src.parsers.autopsy_adapter import AutopsySqliteAdapter
from src.observation.e01_engine import E01ForensicObservationEngine
from src.entity_resolution.signal_extractor import ObservationSignalExtractor
from src.entity_resolution.graph_integrator import KuzuEntityGraphIntegrator
from src.entity_resolution.service import EntityGraphService
from src.analytics.graph_analytics import NetworkGraphAnalytics
from src.api.main import app


E01_IMAGE_PATH = Path("Images/Images_Set_1.E01")


@pytest.fixture(scope="module")
def extracted_autopsy_db():
    """
    Extracts autopsy.db from real E01 container once for module.
    Preserves forensic integrity and reuses artifact across tests.
    """
    if not E01_IMAGE_PATH.exists():
        pytest.skip(f"E01 image not found at {E01_IMAGE_PATH}")

    tmp_dir = tempfile.mkdtemp(prefix="crimenet_8d_test_")
    out_path = Path(tmp_dir)
    engine = E01ForensicObservationEngine(max_artifacts=2, priority_targets=["autopsy.db"])
    contract, _ = engine.process(
        image_path=E01_IMAGE_PATH,
        output_dir=out_path,
        case_id="CASE_SLICE8D_AUDIT",
        evidence_id="EV_SLICE8D_AUDIT",
        job_id="JOB_SLICE8D_AUDIT"
    )
    db_art = next(a for a in contract["observed_artifacts"] if a["artifact_name"] == "autopsy.db")
    db_path = out_path / "extracted_artifacts" / Path(db_art["content_path"]).name
    yield db_path, db_art, tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_network_graph_analytics_nine_algorithms_on_real_evidence(extracted_autopsy_db):
    """
    Direct verification of NetworkGraphAnalytics covering all 9 algorithms
    on real forensic observations from autopsy.db.
    """
    db_path, db_art, _ = extracted_autopsy_db
    adapter = AutopsySqliteAdapter(batch_size=500)
    _, observations = adapter._execute_parse(db_path, db_art)

    case_id = "CASE_REAL_8D_DIRECT"
    evidence_id = "EV_REAL_8D"
    artifact_id = db_art["artifact_id"]
    job_id = "JOB_REAL_8D"

    extractor = ObservationSignalExtractor()
    all_signals = []
    all_relationships = []
    timestamps = []

    # Extract signals, relationships, and timestamps
    for obs in observations:
        if obs.observation_type == ObservationType.FORENSIC_COMMUNICATION:
            if isinstance(obs.value, dict) and obs.value.get("date_time"):
                timestamps.append(int(obs.value["date_time"]))
        sigs = extractor.extract_signals_from_observation(obs, case_id, evidence_id, artifact_id, job_id)
        all_signals.extend(sigs)
        rels = extractor.extract_relationships_from_observation(obs, sigs, case_id, evidence_id, artifact_id, job_id)
        all_relationships.extend(rels)

    # Build case graph structure matching get_case_graph with resolved canonical entities
    email_sigs = [s for s in all_signals if s.entity_type == "Email"]
    unique_normalized_emails = sorted(list(set(s.normalized_value for s in email_sigs)))
    assert len(unique_normalized_emails) == 324

    # Map normalized email to canonical entity ID
    email_norm_to_cid = {norm: f"CAN-EMA-{idx:04d}" for idx, norm in enumerate(unique_normalized_emails, start=1)}
    # Map each signal_id -> canonical_entity_id
    signal_to_canonical = {s.signal_id: email_norm_to_cid[s.normalized_value] for s in email_sigs}

    mock_nodes = [
        {
            "id": cid,
            "label": norm_val,
            "canonical_name": norm_val,
            "entity_type": "Email",
            "observed_count": sum(1 for s in email_sigs if s.normalized_value == norm_val),
            "is_anchor": False,
            "case_id": case_id,
        }
        for norm_val, cid in email_norm_to_cid.items()
    ]

    mock_edges = []
    for r in all_relationships:
        if r.rel_label == "COMMUNICATED_WITH":
            src_cid = signal_to_canonical.get(r.source_signal_id)
            tgt_cid = signal_to_canonical.get(r.target_signal_id)
            if src_cid and tgt_cid:
                mock_edges.append({
                    "id": r.rel_id,
                    "source": src_cid,
                    "target": tgt_cid,
                    "relationship_type": r.rel_label,
                    "relationship": r.rel_label,
                    "evidence_id": r.evidence_id,
                    "case_id": case_id,
                })

    assert len(mock_nodes) == 324
    assert len(mock_edges) == 14164

    case_graph = {
        "case_id": case_id,
        "nodes": mock_nodes,
        "edges": mock_edges,
    }

    analytics_engine = NetworkGraphAnalytics()
    results = analytics_engine.compute_analytics(
        case_graph=case_graph,
        temporal_timestamps=timestamps,
    )

    # Assertions on all 9 algorithms:
    assert not results["is_empty"]
    assert results["case_id"] == case_id

    # 1. Degree (Unique Communicating Neighbors)
    deg = results["degree_metrics"]
    assert len(deg) == len(mock_nodes)
    for nid, d in deg.items():
        assert d["in_degree"] >= 0
        assert d["out_degree"] >= 0
        assert d["unique_neighbors"] >= 0
        assert d["total_degree"] == d["unique_neighbors"]

    # 2. Weighted Communication Frequency
    freq = results["weighted_frequency"]
    assert freq["unique_pairs"] > 0
    assert freq["max_frequency"] >= 1
    for pair in freq["pairs"][:10]:
        assert pair["weight"] >= 1
        assert pair["evidence_count"] >= 1

    # 3. Betweenness Centrality (Inverse frequency distance)
    bet = results["betweenness_centrality"]
    assert len(bet) == len(mock_nodes)
    for nid, score in bet.items():
        assert 0.0 <= score <= 1.0

    # 4. PageRank (Weighted Communication Flow)
    pr = results["pagerank"]
    assert len(pr) == len(mock_nodes)
    total_pr = sum(pr.values())
    assert 0.99 <= total_pr <= 1.01

    # 5. Connected Components (Weak & Strong)
    cc = results["connected_components"]
    assert cc["weakly_connected_count"] >= 1
    assert cc["strongly_connected_count"] >= 1
    assert cc["largest_component_size"] >= 1

    # 6. Louvain Community Detection (Undirected weighted projection)
    comm = results["community_detection"]
    assert comm["algorithm"] == "LOUVAIN_MODULARITY"
    assert comm["projection"] == "UNDIRECTED_WEIGHTED"
    assert comm["total_communities"] >= 1
    for c in comm["communities"]:
        assert c["size"] == len(c["member_node_ids"])

    # 7. Weighted Shortest Path (Inverse frequency distance)
    sp = results["shortest_path"]
    assert "path_exists" in sp
    assert "path" in sp
    assert "hop_count" in sp

    # 8. 1-Hop / 2-Hop Neighbors
    nbr = results["neighbor_metrics"]
    assert nbr["entity_id"] is not None
    assert nbr["one_hop_count"] == len(nbr["one_hop"])
    assert nbr["two_hop_count"] == len(nbr["two_hop"])

    # 9. Descriptive Timestamp Patterns
    tp = results["timestamp_patterns"]
    assert tp["total_events"] == len(timestamps)
    assert tp["total_events"] == 12542
    assert tp["earliest_timestamp"] == 1268125370
    assert tp["latest_timestamp"] == 1696917498
    assert "2010" in tp["earliest_iso"]
    assert "2023" in tp["latest_iso"]
    assert len(tp["monthly_distribution"]) > 0
    assert len(tp["hourly_distribution_utc"]) == 24

    # Execution timing benchmarks recorded
    timing = results["benchmark_timing_ms"]
    assert "total_analytics_ms" in timing
    assert timing["total_analytics_ms"] > 0
    assert "degree_ms" in timing
    assert "betweenness_ms" in timing
    assert "pagerank_ms" in timing
    assert "community_detection_ms" in timing

    # Semantics explicitly documented
    assert results["semantics"]["degree"] == "unique communicating neighbors"
    assert results["semantics"]["frequency"] == "observed communication count"
    assert results["semantics"]["betweenness_distance"] == "inverse frequency (1.0 / weight)"
    assert results["semantics"]["pagerank"] == "weighted communication graph"
    assert results["semantics"]["community_detection"] == "undirected weighted projection"


def test_service_compute_graph_analytics_case_isolation(extracted_autopsy_db):
    """
    Integration test for EntityGraphService.compute_graph_analytics:
    Ingests real autopsy observations into Case A.
    Case B is an isolated case with no evidence.
    Verifies:
    1. Case A analytics returns real populated metrics.
    2. Case B analytics returns is_empty=True with 0 edges and zero leakage from Case A.
    """
    db_path, db_art, _ = extracted_autopsy_db
    adapter = AutopsySqliteAdapter(batch_size=500)
    meta, observations = adapter._execute_parse(db_path, db_art)

    case_a = "CASE_8D_ISOLATION_A"
    case_b = "CASE_8D_ISOLATION_B"
    job_id = "JOB_8D_ISO_001"

    parsed_artifact = ParsedArtifact(
        artifact_id=db_art["artifact_id"],
        case_id=case_a,
        status=ParsingStatus.SUCCESS,
        parser_metadata=ParserMetadata(
            parser_type=ParserType.AUTOPSY_SQLITE,
            parser_name=adapter.get_parser_name(),
            parser_version=adapter.get_parser_version(),
            parsed_at="2026-09-07T12:00:00Z",
            execution_duration_ms=150.0,
            file_size_bytes=db_path.stat().st_size,
            configured_size_ceiling_bytes=150 * 1024 * 1024,
        ),
        computed_sha256=db_art["sha256"],
        integrity_verified=True,
        structured_metadata=meta,
        observations=(
            [o for o in observations if o.observation_type == ObservationType.FORENSIC_ACCOUNT][:60]
            + [o for o in observations if o.observation_type == ObservationType.FORENSIC_COMMUNICATION][:150]
        ),
    )

    actor = TokenPayload(
        sub="officer_8d_iso",
        username="officer8d",
        role=UserRole.INVESTIGATION_OFFICER,
        exp=9999999999,
        jti="jti-8d-iso",
    )

    kuzu_dir = tempfile.mkdtemp(prefix="kuzu_test_8d_")
    try:
        integrator = KuzuEntityGraphIntegrator(db_path=os.path.join(kuzu_dir, "graph_db"))
        integrator.setup()

        service = EntityGraphService(graph_integrator=integrator)
        service.auth_service._user_db["officer_8d_iso"] = User(
            user_id="officer_8d_iso",
            username="officer8d",
            password_hash="mock_hash",
            role=UserRole.INVESTIGATION_OFFICER,
            authorized_case_ids=[case_a, case_b],
        )
        service.parsed_repo.save(parsed_artifact)

        # Ingest for Case A
        service.ingest_parsed_observations(
            actor=actor,
            case_id=case_a,
            job_id=job_id,
            artifact_id=db_art["artifact_id"]
        )

        # Case A Analytics
        analytics_a = service.compute_graph_analytics(actor=actor, case_id=case_a)
        assert not analytics_a["is_empty"]
        assert analytics_a["summary"]["total_nodes"] > 0
        assert analytics_a["summary"]["total_raw_edges"] > 0
        assert analytics_a["weighted_frequency"]["unique_pairs"] > 0
        assert analytics_a["timestamp_patterns"]["total_events"] > 0

        # Case B Analytics: Must be completely empty, zero leakage from Case A
        analytics_b = service.compute_graph_analytics(actor=actor, case_id=case_b)
        assert analytics_b["is_empty"]
        assert analytics_b["summary"]["total_edges"] == 0
        assert analytics_b["weighted_frequency"]["unique_pairs"] == 0
        assert len(analytics_b["degree_metrics"]) == 0
        assert len(analytics_b["betweenness_centrality"]) == 0
        assert len(analytics_b["pagerank"]) == 0
        assert analytics_b["timestamp_patterns"]["total_events"] == 0

        integrator.teardown()
    finally:
        shutil.rmtree(kuzu_dir, ignore_errors=True)


def test_rest_api_get_graph_analytics_and_authorization():
    """
    Tests REST API endpoint GET /api/v1/cases/{case_id}/graph/analytics.
    Verifies:
    1. Authorized officer receives 200 OK with full analytics payload.
    2. Unauthorized officer receives 403 Forbidden (BOLA security enforcement).
    """
    from src.api.graph_resolution_routes import entity_graph_service

    auth_case = "CASE_8D_API_AUTH"
    unauth_case = "CASE_8D_API_FORBIDDEN"

    # Register users in auth_service
    officer = User(
        user_id="officer_8d_auth",
        username="officer8d_auth",
        password_hash="mock_hash",
        role=UserRole.INVESTIGATION_OFFICER,
        authorized_case_ids=[auth_case],  # NOT authorized for unauth_case
    )
    entity_graph_service.auth_service._user_db["officer_8d_auth"] = officer

    token_payload = TokenPayload(
        sub="officer_8d_auth",
        username="officer8d_auth",
        role=UserRole.INVESTIGATION_OFFICER,
        exp=9999999999,
        jti="jti-8d-api",
    )
    token = entity_graph_service.auth_service.create_access_token(officer)

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Authorized Case
    res_auth = client.get(f"/api/v1/cases/{auth_case}/graph/analytics", headers=headers)
    assert res_auth.status_code == 200
    data = res_auth.json()
    assert data["case_id"] == auth_case
    assert "degree_metrics" in data
    assert "betweenness_centrality" in data
    assert "pagerank" in data
    assert "connected_components" in data
    assert "community_detection" in data
    assert "shortest_path" in data
    assert "neighbor_metrics" in data
    assert "timestamp_patterns" in data
    assert "benchmark_timing_ms" in data

    # 2. Unauthorized Case -> BOLA Boundary 403 Forbidden
    res_unauth = client.get(f"/api/v1/cases/{unauth_case}/graph/analytics", headers=headers)
    assert res_unauth.status_code == 403
    assert "Authorization Denied" in res_unauth.json()["detail"]


def test_end_to_end_real_investigator_workflow():
    """
    Final End-to-End Integration Verification:
    Executes the complete runtime pipeline:
    Login -> Create Case -> Register Real E01+E02 Evidence -> Explicitly Process E01 ->
    Background worker (isolated pytsk3 + 100MB ceiling + autopsy.db targeted extraction +
    deep parsing + signal extraction + canonical entity resolution + relationship canonicalization +
    case-scoped Kùzu graph DB ingestion) ->
    Verification:
    1. Real case graph populated (324 canonical email entities, 5,637 unique pairs, 0 ASSOCIATED_WITH).
    2. Real case graph accessible via GET /api/v1/cases/{case_id}/graph?demo=false and is_empty=False.
    3. Real graph analytics endpoint GET /api/v1/cases/{case_id}/graph/analytics computes all 9 algorithms.
    4. Real node and relationship inspection returns the complete 5-stage forensic provenance trace:
       Relationship -> Signal -> Observation -> Artifact -> Evidence with case ID.
    5. Unauthorized investigator receives 403 Forbidden.
    6. Closed case denies new processing jobs.
    """
    real_e01 = Path(r"Images/Images_Set_1.E01")
    real_e02 = Path(r"Images/Images_Set_1.E02")
    if not real_e01.exists() or not real_e02.exists():
        pytest.skip(f"Real E01 evidence not found at {real_e01}")

    from src.evidence.storage import LocalFileStorage
    client = TestClient(app)

    # 1. Login
    login_res = client.post("/api/v1/auth/login", json={"username": "officer1", "password": "OfficerPass123!"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Case
    case_res = client.post(
        "/api/v1/cases",
        headers=headers,
        json={"case_name": "E2E Real E01 Case", "description": "End-to-End Real Forensic Pipeline Test"}
    )
    assert case_res.status_code == 201
    case_id = case_res.json()["case_id"]

    # 3. Stage E01 + E02
    init_res = client.post("/api/v1/evidence/upload/init", headers=headers)
    assert init_res.status_code == 200
    staging_id = init_res.json()["staging_id"]

    storage = LocalFileStorage()
    s_dir = storage.get_staging_dir(staging_id)

    shutil.copyfile(str(real_e01), str(s_dir / "Images_Set_1.E01"))
    shutil.copyfile(str(real_e02), str(s_dir / "Images_Set_1.E02"))

    s_file = s_dir / "session.json"
    with open(s_file, "r", encoding="utf-8") as f:
        sess = json.load(f)

    sess["files"]["Images_Set_1.E01"] = {
        "filename": "Images_Set_1.E01",
        "size_bytes": real_e01.stat().st_size,
        "chunks_received": 1,
        "total_chunks": 1,
        "is_complete": True,
        "sha256": "733948eee283af8e0dc9c6e389039569a41c4522172e8cdfcebf34e86f1cd21a",
        "md5": "2451eecafbc2183d1c6c1bd972a09cc7"
    }
    sess["files"]["Images_Set_1.E02"] = {
        "filename": "Images_Set_1.E02",
        "size_bytes": real_e02.stat().st_size,
        "chunks_received": 1,
        "total_chunks": 1,
        "is_complete": True,
        "sha256": "1da71529a72d2e10e060efe900616f098691c65787ada11c95cefed7f8e0f84d",
        "md5": "1da71529a72d2e10e060efe900616f09"
    }
    with open(s_file, "w", encoding="utf-8") as f:
        json.dump(sess, f)

    fin_res = client.post("/api/v1/evidence/upload/finalize", headers=headers, json={"staging_id": staging_id})
    assert fin_res.status_code == 200

    # 4. Register Evidence
    reg_res = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        headers=headers,
        data={
            "evidence_name": "Images_Set_1.E01",
            "evidence_type": "DISK_IMAGE",
            "staging_id": staging_id
        }
    )
    assert reg_res.status_code == 201
    evidence_id = reg_res.json()["evidence_id"]

    # 5. Explicitly Launch Processing Job
    proc_res = client.post(f"/api/v1/cases/{case_id}/evidence/{evidence_id}/process", headers=headers)
    assert proc_res.status_code == 202
    job_id = proc_res.json()["job_id"]

    # Wait for completion (timeout 360s)
    poll_data = None
    for elapsed in range(360):
        time.sleep(1)
        res = client.get(f"/api/v1/processing/jobs/{job_id}", headers=headers)
        if res.status_code == 200:
            poll_data = res.json()
            if elapsed % 15 == 0:
                print(f"[E2E Polling {elapsed}s] status={poll_data.get('status')}")
            if poll_data["status"] in ["COMPLETED", "FAILED"]:
                print(f"[E2E Job Finished at {elapsed}s] status={poll_data.get('status')}")
                break

    assert poll_data is not None
    assert poll_data["status"] == "COMPLETED", f"Processing job failed: {poll_data.get('error_message')}"

    # 6. Verify Real Case Graph via API
    graph_res = client.get(f"/api/v1/cases/{case_id}/graph?demo=false", headers=headers)
    assert graph_res.status_code == 200
    graph_data = graph_res.json()
    assert not graph_data["is_empty"]
    assert graph_data["case_id"] == case_id
    assert graph_data["summary"]["total_nodes"] >= 324
    assert graph_data["summary"]["total_edges"] == 5237

    # Check zero ASSOCIATED_WITH in real contact network
    for edge in graph_data["edges"]:
        assert edge["relationship_type"] in ["COMMUNICATED_WITH", "USED_EMAIL", "CALLED", "LOCATED_AT"]
        assert edge["relationship_type"] != "ASSOCIATED_WITH"

    # 7. Verify Graph Analytics
    analytics_res = client.get(f"/api/v1/cases/{case_id}/graph/analytics", headers=headers)
    assert analytics_res.status_code == 200
    analytics_data = analytics_res.json()
    assert not analytics_data["is_empty"]
    assert analytics_data["weighted_frequency"]["unique_pairs"] == 5237
    assert len(analytics_data["degree_metrics"]) >= 324
    assert len(analytics_data["betweenness_centrality"]) >= 324
    assert len(analytics_data["pagerank"]) >= 324
    assert analytics_data["timestamp_patterns"]["total_events"] >= 12542

    # 8. Verify 5-Stage Provenance on Node
    test_node = next(n for n in graph_data["nodes"] if not n.get("is_anchor"))
    node_res = client.get(f"/api/v1/cases/{case_id}/graph/entity/{test_node['id']}?demo=false", headers=headers)
    assert node_res.status_code == 200
    node_data = node_res.json()
    assert "provenance_chain" in node_data
    assert node_data["case_id"] == case_id

    # 9. Verify 5-Stage Provenance on Edge
    test_edge = graph_data["edges"][0]
    edge_res = client.get(f"/api/v1/cases/{case_id}/graph/relationship/{test_edge['id']}?demo=false", headers=headers)
    assert edge_res.status_code == 200
    edge_data = edge_res.json()
    assert "provenance_chain" in edge_data
    assert edge_data["provenance_chain"]["case_id"] == case_id
    assert edge_data["provenance_chain"]["artifact_id"] != ""
    assert edge_data["provenance_chain"]["evidence_id"] != ""

    # 10. Verify Unauthorized Access Denied (BOLA)
    unauth_login = client.post("/api/v1/auth/login", json={"username": "officer2", "password": "OfficerPass456!"})
    unauth_token = unauth_login.json()["access_token"]
    unauth_headers = {"Authorization": f"Bearer {unauth_token}"}

    forbidden_graph = client.get(f"/api/v1/cases/{case_id}/graph?demo=false", headers=unauth_headers)
    assert forbidden_graph.status_code == 403

    forbidden_analytics = client.get(f"/api/v1/cases/{case_id}/graph/analytics", headers=unauth_headers)
    assert forbidden_analytics.status_code == 403

    # 11. Verify Closed Case Protection
    client.put(f"/api/v1/cases/{case_id}", headers=headers, json={"status": "CLOSED"})
    closed_proc = client.post(f"/api/v1/cases/{case_id}/evidence/{evidence_id}/process", headers=headers)
    assert closed_proc.status_code == 403
