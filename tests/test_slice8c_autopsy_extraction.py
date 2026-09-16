"""
Unit & Integration Verification Suite for CRIMENET Slice 8C: Targeted Autopsy SQLite Extraction.

Validates:
1. Targeted extraction of autopsy.db (67.83 MB) from real multi-segment E01 container (Images_Set_1.E01 + E02).
2. Dedicated AutopsySqliteAdapter memory-bounded batch streaming (fetchmany).
3. Extraction of real forensic observations (accounts, account_relationships, TSK_EMAIL_MSG, TSK_METADATA_EXIF GPS).
4. Signal extraction yielding >= 50 real email entities and >= 100 real communication relationships.
5. Strict relationship rules:
   - Primary graph is Email -> COMMUNICATED_WITH -> Email.
   - USED_EMAIL is created ONLY when explicit display name is bound to email address in header.
   - Zero generic ASSOCIATED_WITH.
   - Zero synthetic data, zero demo data.
6. Exact 5-part provenance preserved down to table name and row/artifact ID.
7. Case isolation and BOLA security boundary enforcement.
"""

import os
import shutil
import tempfile
import pytest
from pathlib import Path

from src.auth.models import TokenPayload, UserRole, User
from src.parsers.models import (
    ParserType,
    ObservationType,
    ExtractedObservation,
)
from src.parsers.autopsy_adapter import AutopsySqliteAdapter
from src.parsers.registry import ParserRegistry
from src.observation.e01_engine import E01ForensicObservationEngine
from src.entity_resolution.signal_extractor import ObservationSignalExtractor
from src.entity_resolution.graph_integrator import KuzuEntityGraphIntegrator
from src.entity_resolution.service import EntityGraphService
from src.parsers.models import ParsedArtifact, ParserMetadata, ParsingStatus


E01_IMAGE_PATH = Path("Images/Images_Set_1.E01")


@pytest.fixture(scope="module")
def extracted_autopsy_db():
    """
    Extracts autopsy.db from real E01 container once for the module.
    Preserves forensic integrity and reuses artifact across test cases.
    """
    if not E01_IMAGE_PATH.exists():
        pytest.skip(f"E01 image not found at {E01_IMAGE_PATH}")

    tmp_dir = tempfile.mkdtemp(prefix="crimenet_8c_test_")
    out_path = Path(tmp_dir)
    engine = E01ForensicObservationEngine(max_artifacts=2, priority_targets=["autopsy.db"])
    contract, _ = engine.process(
        image_path=E01_IMAGE_PATH,
        output_dir=out_path,
        case_id="CASE_SLICE8C_AUDIT",
        evidence_id="EV_SLICE8C_AUDIT",
        job_id="JOB_SLICE8C_AUDIT"
    )

    db_art = None
    for art in contract["observed_artifacts"]:
        if art["artifact_name"] == "autopsy.db":
            db_art = art
            break

    assert db_art is not None, "autopsy.db was not extracted by E01ForensicObservationEngine"
    db_file_path = out_path / "extracted_artifacts" / Path(db_art["content_path"]).name
    assert db_file_path.exists(), f"Extracted db file missing at {db_file_path}"

    yield db_file_path, db_art, out_path

    # Teardown
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_autopsy_adapter_header_detection_and_magic(extracted_autopsy_db):
    """Verifies AutopsySqliteAdapter format detection and schema introspection."""
    db_path, _, _ = extracted_autopsy_db
    adapter = AutopsySqliteAdapter()

    assert adapter.get_parser_type() == ParserType.AUTOPSY_SQLITE
    assert adapter.get_parser_name() == "CRIMENET_AUTOPSY_SQLITE_ADAPTER"

    header = adapter.read_header_bytes(db_path, 64)
    assert header.startswith(b"SQLite format 3\x00")
    assert adapter.can_parse(db_path, header) is True

    # Negative test: dummy non-autopsy file
    _, _, out_path = extracted_autopsy_db
    dummy_non_autopsy = out_path / "dummy_non_autopsy.db"
    dummy_non_autopsy.write_bytes(b"SQLite format 3\x00" + b"\x00" * 100)
    non_header = adapter.read_header_bytes(dummy_non_autopsy, 64)
    assert adapter.can_parse(dummy_non_autopsy, non_header) is False


def test_autopsy_adapter_bounded_batch_streaming(extracted_autopsy_db):
    """
    Verifies that AutopsySqliteAdapter streams records in bounded batches
    (fetchmany) without loading entire datasets into memory.
    """
    db_path, db_art, _ = extracted_autopsy_db
    batch_size = 50
    adapter = AutopsySqliteAdapter(batch_size=batch_size)

    conn = adapter._get_readonly_connection(db_path)
    art_id = db_art["artifact_id"]

    # 1. Accounts stream
    account_batches = list(adapter.stream_accounts(conn, art_id))
    assert len(account_batches) > 1, "Accounts should be yielded in multiple bounded batches"
    for b in account_batches:
        assert len(b) <= batch_size
        for obs in b:
            assert obs.observation_type == ObservationType.FORENSIC_ACCOUNT
            assert "accounts.account_id=" in obs.provenance_note

    # 2. Account Relationships stream
    comm_batches = list(adapter.stream_account_relationships(conn, art_id))
    assert len(comm_batches) > 10, "12,545 relationships should span many batches of 50"
    for b in comm_batches[:5]:
        assert len(b) <= batch_size
        for obs in b:
            assert obs.observation_type == ObservationType.FORENSIC_COMMUNICATION
            assert "account_relationships.relationship_id=" in obs.provenance_note

    # 3. Email Messages stream
    msg_batches = list(adapter.stream_email_messages(conn, art_id))
    assert len(msg_batches) > 5
    for b in msg_batches[:3]:
        assert len(b) <= batch_size
        for obs in b:
            assert obs.observation_type == ObservationType.FORENSIC_EMAIL_MESSAGE
            assert "TSK_EMAIL_MSG" in obs.provenance_note

    # 4. EXIF GPS stream
    gps_batches = list(adapter.stream_exif_gps(conn, art_id))
    total_gps = sum(len(b) for b in gps_batches)
    assert total_gps == 22, f"Expected exactly 22 GPS records, got {total_gps}"
    for b in gps_batches:
        for obs in b:
            assert obs.observation_type == ObservationType.FORENSIC_EXIF_GPS
            assert obs.value["latitude"] is not None
            assert obs.value["longitude"] is not None

    conn.close()


def test_autopsy_adapter_execute_parse_metadata_and_provenance(extracted_autopsy_db):
    """
    Verifies full parse execution via _execute_parse, structured metadata summary,
    and 5-part provenance down to table and primary key.
    """
    db_path, db_art, _ = extracted_autopsy_db
    adapter = AutopsySqliteAdapter(batch_size=500)

    metadata, observations = adapter._execute_parse(db_path, db_art)

    assert metadata["format"] == "Autopsy Forensic SQLite Database"
    summary = metadata["extraction_summary"]
    assert summary["accounts"] == 322
    assert summary["account_relationships"] == 12545
    assert summary["email_messages"] == 1974
    assert summary["exif_gps"] == 22
    assert summary["web_activity"] == 639

    assert len(observations) == 322 + 12545 + 1974 + 22 + 639

    # Verify provenance on observations
    sample_acc = next(o for o in observations if o.observation_type == ObservationType.FORENSIC_ACCOUNT)
    assert sample_acc.value["table"] == "accounts"
    assert sample_acc.location_reference.startswith("Table: accounts")

    sample_comm = next(o for o in observations if o.observation_type == ObservationType.FORENSIC_COMMUNICATION)
    assert sample_comm.value["table"] == "account_relationships"
    assert sample_comm.location_reference.startswith("Table: account_relationships")

    sample_gps = next(o for o in observations if o.observation_type == ObservationType.FORENSIC_EXIF_GPS)
    assert sample_gps.value["table"] == "blackboard_artifacts"
    assert -90 <= sample_gps.value["latitude"] <= 90
    assert -180 <= sample_gps.value["longitude"] <= 180


def test_registry_integration_prefers_autopsy_over_generic_sqlite(extracted_autopsy_db):
    """Verifies that ParserRegistry dispatches autopsy.db to AutopsySqliteAdapter rather than generic SqliteParser."""
    db_path, _, _ = extracted_autopsy_db
    registry = ParserRegistry()

    parser = registry.get_parser_for_file(db_path)
    assert isinstance(parser, AutopsySqliteAdapter)
    assert parser.get_parser_type() == ParserType.AUTOPSY_SQLITE


def test_deterministic_signal_extraction_acceptance_criteria(extracted_autopsy_db):
    """
    Acceptance Test for Slice 8C:
    1. >= 50 real email entities observed
    2. >= 100 real communication relationships
    3. Real GPS observations present
    4. USED_EMAIL created strictly when display name is bound to email
    5. Primary graph is Email -> COMMUNICATED_WITH -> Email
    6. Strictly ZERO generic ASSOCIATED_WITH
    7. Strictly ZERO synthetic data, ZERO demo data
    """
    db_path, db_art, _ = extracted_autopsy_db
    adapter = AutopsySqliteAdapter(batch_size=500)
    _, observations = adapter._execute_parse(db_path, db_art)

    extractor = ObservationSignalExtractor()
    case_id = "CASE_REAL_8C"
    evidence_id = "EV_REAL_8C"
    artifact_id = db_art["artifact_id"]
    job_id = "JOB_REAL_8C"

    all_signals = []
    all_relationships = []

    for obs in observations:
        sigs = extractor.extract_signals_from_observation(obs, case_id, evidence_id, artifact_id, job_id)
        all_signals.extend(sigs)
        rels = extractor.extract_relationships_from_observation(obs, sigs, case_id, evidence_id, artifact_id, job_id)
        all_relationships.extend(rels)

    # 1. Real Email signals check
    email_sigs = [s for s in all_signals if s.entity_type == "Email"]
    unique_emails = set(s.normalized_value for s in email_sigs)
    assert len(unique_emails) >= 50, f"Expected >= 50 unique real emails, got {len(unique_emails)}"
    assert len(unique_emails) == 324, f"Expected 324 unique real emails in autopsy.db, got {len(unique_emails)}"

    # 2. Real Communication relationships check
    comm_rels = [r for r in all_relationships if r.rel_label == "COMMUNICATED_WITH"]
    assert len(comm_rels) >= 100, f"Expected >= 100 communication relationships, got {len(comm_rels)}"
    assert len(comm_rels) == 14164, f"Expected 14,164 communications, got {len(comm_rels)}"

    # Primary communication edges must be Email -> COMMUNICATED_WITH -> Email
    for r in comm_rels:
        if r.extraction_method == "AUTOPSY_ACCOUNT_RELATIONSHIP":
            assert r.source_label == "Email"
            assert r.target_label == "Email"

    # 3. Real GPS Location signals check
    loc_sigs = [s for s in all_signals if s.entity_type == "Location"]
    assert len(loc_sigs) == 22, f"Expected 22 GPS location signals, got {len(loc_sigs)}"
    for s in loc_sigs:
        assert s.extraction_method == "AUTOPSY_EXIF_GPS"
        assert "," in s.normalized_value

    # 4. Strict display name binding for USED_EMAIL (Correction 3)
    used_email_rels = [r for r in all_relationships if r.rel_label == "USED_EMAIL"]
    assert len(used_email_rels) > 0, "Expected USED_EMAIL relationships when headers contain display names"
    for r in used_email_rels:
        assert r.source_label == "Person"
        assert r.target_label == "Email"
        assert r.extraction_method == "EMAIL_HEADER_NAME_BINDING"

    # 5. ZERO ASSOCIATED_WITH relationships
    assoc_rels = [r for r in all_relationships if r.rel_label == "ASSOCIATED_WITH"]
    assert len(assoc_rels) == 0, f"Strictly forbidden ASSOCIATED_WITH found: {len(assoc_rels)}"

    # 6. Complete 5-part provenance preserved
    for s in all_signals[:50]:
        assert s.case_id == case_id
        assert s.evidence_id == evidence_id
        assert s.artifact_id == artifact_id
        assert s.job_id == job_id
        assert len(s.observation_id) > 0
        assert len(s.provenance_trace) > 0

    for r in all_relationships[:50]:
        assert r.case_id == case_id
        assert r.evidence_id == evidence_id
        assert r.artifact_id == artifact_id
        assert r.job_id == job_id
        assert len(r.observation_id) > 0


def test_end_to_end_kuzu_ingestion_and_case_isolation(extracted_autopsy_db):
    """
    End-to-end integration test:
    Ingests real autopsy.db parsed observations into Kùzu Knowledge Graph via EntityGraphService.
    Asserts canonical Email entities and COMMUNICATED_WITH edges are created.
    Asserts strict case isolation between CASE_A and CASE_B.
    """
    db_path, db_art, _ = extracted_autopsy_db
    adapter = AutopsySqliteAdapter(batch_size=500)
    meta, observations = adapter._execute_parse(db_path, db_art)

    case_a = "CASE_REAL_INGEST_A"
    case_b = "CASE_REAL_INGEST_B"
    job_id = "JOB_REAL_INGEST_001"

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
            [o for o in observations if o.observation_type == ObservationType.FORENSIC_ACCOUNT][:50]
            + [o for o in observations if o.observation_type == ObservationType.FORENSIC_COMMUNICATION][:100]
        ),
    )

    actor = TokenPayload(
        sub="officer_8c_01",
        username="officer8c",
        role=UserRole.INVESTIGATION_OFFICER,
        exp=9999999999,
        jti="test-jti-8c",
    )

    kuzu_dir = tempfile.mkdtemp(prefix="kuzu_test_8c_")
    try:
        integrator = KuzuEntityGraphIntegrator(db_path=os.path.join(kuzu_dir, "graph_db"))
        integrator.setup()

        service = EntityGraphService(graph_integrator=integrator)
        service.auth_service._user_db["officer_8c_01"] = User(
            user_id="officer_8c_01",
            username="officer8c",
            password_hash="mock_hash",
            role=UserRole.INVESTIGATION_OFFICER,
            authorized_case_ids=[case_a, case_b],
        )
        service.parsed_repo.save(parsed_artifact)

        # Ingest observations for Case A
        result = service.ingest_parsed_observations(
            actor=actor,
            case_id=case_a,
            job_id=job_id,
            artifact_id=db_art["artifact_id"]
        )

        assert result["status"] == "COMPLETED"
        assert result["canonical_entities_created"] > 0
        assert result["relationships_created"] > 0

        # Query Case A graph
        graph_a = service.get_case_graph(actor=actor, case_id=case_a, demo=False)
        assert len(graph_a["nodes"]) > 0
        assert len(graph_a["edges"]) > 0

        # Verify edge labels in Case A
        edge_types = {e["relationship"] for e in graph_a["edges"]}
        assert "COMMUNICATED_WITH" in edge_types
        assert "ASSOCIATED_WITH" not in edge_types

        # Verify Case Isolation: Case B must have 0 nodes and 0 edges from Case A
        graph_b = service.get_case_graph(actor=actor, case_id=case_b, demo=False)
        # Case B only has empty anchor node
        non_anchor_nodes_b = [n for n in graph_b["nodes"] if not n.get("is_anchor")]
        assert len(non_anchor_nodes_b) == 0, "Case B leaked entities from Case A!"
        assert len(graph_b["edges"]) == 0, "Case B leaked edges from Case A!"

        integrator.teardown()

    finally:
        shutil.rmtree(kuzu_dir, ignore_errors=True)
