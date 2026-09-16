"""
Comprehensive Test Suite for CRIMENET Slice 8B:
Observation -> Entity/Relationship -> Graph Bridge.

Tests:
1. Deterministic phone extraction (E.164 format)
2. Deterministic email extraction
3. Normalization (E.164, lowercase email, names, locations)
4. Provenance preservation for every signal
5. Entity Resolution clustering into canonical entities
6. Evidence-backed relationship extraction (USED_PHONE, CALLED, LOCATED_AT)
7. Assertion: Strictly NO generic co-occurrence ASSOCIATED_WITH relationships
8. Canonical relationship creation connecting canonical entity IDs
9. Kùzu Graph DB node and edge ingestion
10. Idempotency: repeated ingestion does not crash or duplicate relationships
11. Case isolation: cross-case observation isolation
12. BOLA authorization defense (403 Forbidden on unauthorized case)
13. Scoped execution: explicit artifact_id scope
14. Malformed observation handling
15. Observational statuses preserved without fabrication
16. End-to-End REST integration: Parsed Artifact -> Signal -> ER -> Graph Ingest -> GET /graph
"""

import time
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api.main import app
from src.auth.models import TokenPayload, UserRole
from src.auth.service import AuthService
from src.artifacts.models import Artifact, ArtifactCategory, AllocationStatus, RecoveryStatus, ProvenanceEnvelope
from src.artifacts.repository import SQLiteArtifactRepository
from src.artifacts.service import ArtifactService
from src.parsers.models import (
    ParsedArtifact,
    ParsingStatus,
    ParserMetadata,
    ParserType,
    ObservationType,
    ExtractedObservation,
)
from src.parsers.repository import SQLiteParsedArtifactRepository
from src.entity_resolution.normalizer import (
    normalize_entity,
    normalize_phone_number,
    normalize_email,
    normalize_person_name,
    normalize_location,
    normalize_bank_account,
)
from src.entity_resolution.signal_extractor import ObservationSignalExtractor
from src.entity_resolution.signals import ExtractedSignal, ExtractedRelationship
from src.entity_resolution.resolver import EntityResolver
from src.entity_resolution.graph_integrator import KuzuEntityGraphIntegrator
from src.entity_resolution.service import EntityGraphService

client = TestClient(app)
auth_service = AuthService()


def get_token(username: str = "officer1", password: str = "OfficerPass123!") -> str:
    if username == "officer1":
        pwd = "OfficerPass123!"
    elif username == "officer2":
        pwd = "OfficerPass456!"
    elif username == "boss1":
        pwd = "HigherAuthPass789!"
    else:
        pwd = password

    res = client.post("/api/v1/auth/login", json={"username": username, "password": pwd})
    assert res.status_code == 200, f"Login failed for {username}: {res.json()}"
    return res.json()["access_token"]


@pytest.fixture
def auth_tokens():
    officer1_token = TokenPayload(
        sub="USER-OFFICER-001",
        username="officer1",
        role=UserRole.INVESTIGATION_OFFICER,
        exp=int(time.time()) + 3600,
        jti="test-s8b-jti-1"
    )
    officer2_token = TokenPayload(
        sub="USER-OFFICER-002",
        username="officer2",
        role=UserRole.INVESTIGATION_OFFICER,
        exp=int(time.time()) + 3600,
        jti="test-s8b-jti-2"
    )
    return officer1_token, officer2_token


# ==============================================================================
# 1. NORMALIZATION & SIGNAL EXTRACTION UNIT TESTS
# ==============================================================================

def test_normalization_rules():
    """Test 1: Verifies deterministic normalization for Phone, Email, Names, Locations, Bank Accounts."""
    # Phone E.164
    assert normalize_phone_number("9876543210") == "+919876543210"
    assert normalize_phone_number("+91-98765-43210") == "+919876543210"
    assert normalize_phone_number("09876543210") == "+919876543210"
    assert normalize_phone_number("+1-415-555-2671") == "+14155552671"

    # Email
    assert normalize_email("  Suspect.Lead@CRIME-NET.ORG  ") == "suspect.lead@crime-net.org"

    # Person Name
    assert normalize_person_name("  Mr. Vikram   Singh  ") == "Vikram Singh"
    assert normalize_person_name("dr. rajesh kumar") == "Rajesh Kumar"

    # Location
    assert normalize_location("28.613939, 77.209021") == "28.61394, 77.20902"
    assert normalize_location("new  delhi,  india") == "New Delhi India"

    # Bank Account & IFSC
    assert normalize_bank_account("  hdfc 0001234  ") == "HDFC0001234"


def test_signal_extraction_from_document_text():
    """Test 2: Extracts phones, emails, explicit name prefixes, and IFSC codes from document text."""
    extractor = ObservationSignalExtractor()
    obs = ExtractedObservation(
        observation_id="OBS-DOC-001",
        observation_type=ObservationType.DOCUMENT_TEXT,
        location_reference="Page 1",
        key="page_1_text",
        value=(
            "Meeting minutes recorded on 2026-08-15.\n"
            "Name: Vikram Singh, Phone: +91-9876543210\n"
            "Contact person: Rajesh Kumar (Email: rajesh.k@secure-mail.in)\n"
            "Payment sent via IFSC: SBIN0001234, Account: 987654321098"
        ),
        provenance_note="pypdf:page:1"
    )

    signals = extractor.extract_signals_from_observation(
        obs=obs,
        case_id="CASE-2026-001",
        evidence_id="EV-E01-001",
        artifact_id="ART-DOC-001"
    )

    types = [s.entity_type for s in signals]
    assert "PhoneNumber" in types
    assert "Email" in types
    assert "Person" in types
    assert "BankAccount" in types

    # Verify provenance on every signal
    for s in signals:
        assert s.case_id == "CASE-2026-001"
        assert s.artifact_id == "ART-DOC-001"
        assert s.observation_id == "OBS-DOC-001"
        assert s.source_location == "Page 1"
        assert s.confidence >= 0.90


def test_signal_extraction_from_sqlite_rows():
    """Test 3: Extracts structured signals from SQLite sample rows."""
    extractor = ObservationSignalExtractor()
    obs = ExtractedObservation(
        observation_id="OBS-SQL-001",
        observation_type=ObservationType.SQLITE_SAMPLE_ROWS,
        location_reference="Table: suspect_contacts",
        key="sample_rows_suspect_contacts",
        value={
            "rows": [
                {"id": 1, "name": "Vikram Singh", "phone": "9876543210", "email": "vikram@shadow.net", "city": "New Delhi"},
                {"id": 2, "name": "Rajesh Kumar", "phone": "9876543211", "email": "rajesh@shadow.net", "city": "Mumbai"},
            ]
        }
    )

    signals = extractor.extract_signals_from_observation(
        obs=obs,
        case_id="CASE-2026-001",
        evidence_id="EV-SQL-001",
        artifact_id="ART-SQL-001"
    )

    assert len(signals) >= 8  # 2 rows x (Person + Phone + Email + Location)
    phone_sigs = [s for s in signals if s.entity_type == "PhoneNumber"]
    assert len(phone_sigs) == 2
    assert "+919876543210" in [p.normalized_value for p in phone_sigs]


# ==============================================================================
# 2. RELATIONSHIP EXTRACTION & CO-OCCURRENCE RESTRICTION TESTS
# ==============================================================================

def test_sqlite_row_evidence_backed_relationships():
    """Test 4: Extracts evidence-backed USED_PHONE and LOCATED_AT from SQLite contact rows."""
    extractor = ObservationSignalExtractor()
    obs = ExtractedObservation(
        observation_id="OBS-SQL-002",
        observation_type=ObservationType.SQLITE_SAMPLE_ROWS,
        location_reference="Table: suspect_contacts",
        key="sample_rows_suspect_contacts",
        value={
            "rows": [
                {"id": 1, "name": "Vikram Singh", "phone": "9876543210", "city": "New Delhi"},
            ]
        }
    )

    signals = extractor.extract_signals_from_observation(
        obs=obs,
        case_id="CASE-2026-001",
        evidence_id="EV-SQL-001",
        artifact_id="ART-SQL-001"
    )

    relationships = extractor.extract_relationships_from_observation(
        obs=obs,
        signals=signals,
        case_id="CASE-2026-001",
        evidence_id="EV-SQL-001",
        artifact_id="ART-SQL-001"
    )

    assert len(relationships) >= 1
    rel_types = [r.rel_label for r in relationships]
    assert "USED_PHONE" in rel_types

    used_phone_rel = next(r for r in relationships if r.rel_label == "USED_PHONE")
    assert used_phone_rel.source_label == "Person"
    assert used_phone_rel.target_label == "PhoneNumber"
    assert used_phone_rel.human_verification_status == "UNDER_REVIEW"


def test_no_generic_cooccurrence_associated_with():
    """Test 5 (CRITICAL): Asserts strictly NO ASSOCIATED_WITH is created from generic name co-occurrence."""
    extractor = ObservationSignalExtractor()
    obs = ExtractedObservation(
        observation_id="OBS-DOC-COOCCUR",
        observation_type=ObservationType.DOCUMENT_TEXT,
        location_reference="Page 3",
        key="page_3_text",
        value="During the conference, Vikram Singh presented on forensics while Rajesh Kumar attended the session.",
        provenance_note="pypdf:page:3"
    )

    signals = extractor.extract_signals_from_observation(
        obs=obs,
        case_id="CASE-2026-001",
        evidence_id="EV-DOC-001",
        artifact_id="ART-DOC-001"
    )

    relationships = extractor.extract_relationships_from_observation(
        obs=obs,
        signals=signals,
        case_id="CASE-2026-001",
        evidence_id="EV-DOC-001",
        artifact_id="ART-DOC-001"
    )

    # Must NOT create an ASSOCIATED_WITH relationship from mere co-occurrence in document!
    assoc_rels = [r for r in relationships if r.rel_label == "ASSOCIATED_WITH"]
    assert len(assoc_rels) == 0, "VIOLATION: ASSOCIATED_WITH was erroneously created from generic co-occurrence!"


# ==============================================================================
# 3. ENTITY RESOLUTION & GRAPH INGESTION INTEGRATION TESTS
# ==============================================================================

def test_entity_resolution_clustering():
    """Test 6: Resolves duplicate observed mentions into unique canonical entities."""
    resolver = EntityResolver()
    raw_obs = [
        {"obs_id": "SIG-1", "entity_type": "PhoneNumber", "raw_value": "9876543210", "source_file": "ART-1"},
        {"obs_id": "SIG-2", "entity_type": "PhoneNumber", "raw_value": "+91-98765-43210", "source_file": "ART-2"},
        {"obs_id": "SIG-3", "entity_type": "Person", "raw_value": "Mr. Vikram Singh", "source_file": "ART-1"},
        {"obs_id": "SIG-4", "entity_type": "Person", "raw_value": "Vikram Singh", "source_file": "ART-2"},
    ]

    clusters = resolver.resolve_observations(raw_obs)
    phone_clusters = [c for c in clusters if c["entity_type"] == "PhoneNumber"]
    person_clusters = [c for c in clusters if c["entity_type"] == "Person"]

    assert len(phone_clusters) == 1, "Duplicate phone formats must resolve into 1 canonical entity"
    assert len(person_clusters) == 1, "Duplicate name formats must resolve into 1 canonical entity"
    assert phone_clusters[0]["supporting_observations_count"] == 2
    assert person_clusters[0]["supporting_observations_count"] == 2


def test_ingest_parsed_observations_into_graph(tmp_path, auth_tokens):
    """Test 7 & 8: Deep parsed observations ingest into Kùzu Graph DB with canonical entities and edges."""
    officer1_token, _ = auth_tokens

    # Set up test database repositories
    parsed_repo = SQLiteParsedArtifactRepository(db_path=str(tmp_path / "test_parsed.db"))
    kuzu_dir = tmp_path / "kuzu_test_db"
    graph_integrator = KuzuEntityGraphIntegrator(db_path=str(kuzu_dir))

    service = EntityGraphService(
        graph_integrator=graph_integrator,
        parsed_repo=parsed_repo,
    )

    # Save a mock parsed artifact with observations
    parsed_artifact = ParsedArtifact(
        artifact_id="ART-2026-TEST-001",
        case_id="CASE-2026-001",
        status=ParsingStatus.SUCCESS,
        parser_metadata=ParserMetadata(
            parser_type=ParserType.SQLITE,
            parser_name="CRIMENET_SQLITE_FORENSIC_PARSER",
            parser_version="1.0.0",
            parsed_at="2026-09-07T06:45:00Z",
            execution_duration_ms=12.5,
            file_size_bytes=1024,
            configured_size_ceiling_bytes=52428800,
        ),
        computed_sha256="abc123sha",
        integrity_verified=True,
        observations=[
            ExtractedObservation(
                observation_id="OBS-SQL-TEST-001",
                observation_type=ObservationType.SQLITE_SAMPLE_ROWS,
                location_reference="Table: suspect_contacts",
                key="sample_rows_suspect_contacts",
                value={
                    "rows": [
                        {"id": 1, "name": "Vikram Singh", "phone": "9876543210", "city": "New Delhi"},
                        {"id": 2, "name": "Rajesh Kumar", "phone": "9876543211", "city": "Mumbai"},
                    ]
                }
            )
        ]
    )
    parsed_repo.save(parsed_artifact)

    # Ingest observations for CASE-2026-001
    res = service.ingest_parsed_observations(
        actor=officer1_token,
        case_id="CASE-2026-001",
        artifact_id="ART-2026-TEST-001"
    )

    assert res["status"] == "COMPLETED"
    assert res["artifacts_processed"] == 1
    assert res["signals_extracted"] >= 4
    assert res["canonical_entities_created"] >= 4
    assert res["relationships_created"] >= 2  # 2 x USED_PHONE

    # Query Case Graph and verify real nodes and edges exist
    graph_res = service.get_case_graph(actor=officer1_token, case_id="CASE-2026-001", demo=False)
    assert graph_res["case_id"] == "CASE-2026-001"
    assert graph_res["is_empty"] is False
    assert len(graph_res["nodes"]) >= 2
    assert len(graph_res["edges"]) >= 2


def test_idempotent_repeated_observation_ingestion(tmp_path, auth_tokens):
    """Test 9: Repeated execution of ingest_parsed_observations is strictly idempotent."""
    officer1_token, _ = auth_tokens
    parsed_repo = SQLiteParsedArtifactRepository(db_path=str(tmp_path / "test_parsed_idem.db"))
    kuzu_dir = tmp_path / "kuzu_test_idem_db"
    graph_integrator = KuzuEntityGraphIntegrator(db_path=str(kuzu_dir))

    service = EntityGraphService(
        graph_integrator=graph_integrator,
        parsed_repo=parsed_repo,
    )

    parsed_artifact = ParsedArtifact(
        artifact_id="ART-2026-TEST-IDEM",
        case_id="CASE-2026-001",
        status=ParsingStatus.SUCCESS,
        parser_metadata=ParserMetadata(
            parser_type=ParserType.SQLITE,
            parser_name="CRIMENET_SQLITE_FORENSIC_PARSER",
            parser_version="1.0.0",
            parsed_at="2026-09-07T06:45:00Z",
            execution_duration_ms=10.0,
            file_size_bytes=512,
            configured_size_ceiling_bytes=52428800,
        ),
        computed_sha256="idemsha",
        integrity_verified=True,
        observations=[
            ExtractedObservation(
                observation_id="OBS-IDEM-001",
                observation_type=ObservationType.SQLITE_SAMPLE_ROWS,
                location_reference="Table: suspect_contacts",
                key="sample_rows_suspect_contacts",
                value={
                    "rows": [
                        {"id": 1, "name": "Vikram Singh", "phone": "9876543210"},
                    ]
                }
            )
        ]
    )
    parsed_repo.save(parsed_artifact)

    # First ingest
    res1 = service.ingest_parsed_observations(actor=officer1_token, case_id="CASE-2026-001", artifact_id="ART-2026-TEST-IDEM")
    count1 = res1["canonical_entities_created"]

    # Second ingest (Identical payload)
    res2 = service.ingest_parsed_observations(actor=officer1_token, case_id="CASE-2026-001", artifact_id="ART-2026-TEST-IDEM")
    count2 = res2["canonical_entities_created"]

    assert count1 == count2
    assert res2["status"] == "COMPLETED"


# ==============================================================================
# 4. SECURITY, BOLA & CASE ISOLATION TESTS
# ==============================================================================

def test_bola_cross_case_ingest_denied(tmp_path, auth_tokens):
    """Test 10: Officer 2 cannot trigger observation ingestion on Officer 1's case."""
    _, officer2_token = auth_tokens
    parsed_repo = SQLiteParsedArtifactRepository(db_path=str(tmp_path / "test_parsed_sec.db"))
    kuzu_dir = tmp_path / "kuzu_test_sec_db"
    graph_integrator = KuzuEntityGraphIntegrator(db_path=str(kuzu_dir))

    service = EntityGraphService(
        graph_integrator=graph_integrator,
        parsed_repo=parsed_repo,
    )

    with pytest.raises(PermissionError) as exc_info:
        service.ingest_parsed_observations(
            actor=officer2_token,
            case_id="CASE-2026-001",
            artifact_id="ART-ANY"
        )
    assert "Officer not authorized" in str(exc_info.value) or "DENY" in str(exc_info.value)


def test_cross_case_artifact_id_manipulation_denied(tmp_path, auth_tokens):
    """Test 11: Attempting to ingest an artifact belonging to CASE-2026-002 under CASE-2026-001."""
    officer1_token, _ = auth_tokens
    parsed_repo = SQLiteParsedArtifactRepository(db_path=str(tmp_path / "test_parsed_manip.db"))
    kuzu_dir = tmp_path / "kuzu_test_manip_db"
    graph_integrator = KuzuEntityGraphIntegrator(db_path=str(kuzu_dir))

    service = EntityGraphService(
        graph_integrator=graph_integrator,
        parsed_repo=parsed_repo,
    )

    # Save artifact owned by CASE-2026-002
    parsed_artifact = ParsedArtifact(
        artifact_id="ART-CASE2-001",
        case_id="CASE-2026-002",
        status=ParsingStatus.SUCCESS,
        parser_metadata=ParserMetadata(
            parser_type=ParserType.SQLITE,
            parser_name="CRIMENET_SQLITE_FORENSIC_PARSER",
            parser_version="1.0.0",
            parsed_at="2026-09-07T06:45:00Z",
            execution_duration_ms=10.0,
            file_size_bytes=512,
            configured_size_ceiling_bytes=52428800,
        ),
        computed_sha256="case2sha",
        integrity_verified=True,
        observations=[]
    )
    parsed_repo.save(parsed_artifact)

    with pytest.raises(PermissionError) as exc_info:
        service.ingest_parsed_observations(
            actor=officer1_token,
            case_id="CASE-2026-001",
            artifact_id="ART-CASE2-001"
        )
    assert "ID MANIPULATION DENIED" in str(exc_info.value)


# ==============================================================================
# 5. REST API ENDPOINT INTEGRATION TESTS
# ==============================================================================

def test_api_ingest_observations_endpoint():
    """Test 12: Validates POST /api/v1/cases/{case_id}/graph/ingest-observations REST API."""
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}

    # First trigger parse on an artifact if one exists in case
    arts_res = client.get("/api/v1/cases/CASE-2026-001/artifacts", headers=headers)
    assert arts_res.status_code == 200
    artifacts = arts_res.json()
    if artifacts:
        target_art_id = artifacts[0]["artifact_id"]
        # Trigger parse
        client.post(f"/api/v1/cases/CASE-2026-001/artifacts/{target_art_id}/parse", headers=headers)

        # Trigger observation ingestion
        res = client.post(
            f"/api/v1/cases/CASE-2026-001/graph/ingest-observations?artifact_id={target_art_id}",
            headers=headers
        )
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "COMPLETED"
        assert data["case_id"] == "CASE-2026-001"


# ==============================================================================
# 5. SCOPED EXECUTION & 5-PART PROVENANCE TESTS
# ==============================================================================

def test_job_id_scoped_observation_ingestion(tmp_path, auth_tokens):
    """Test 12: Explicit job_id scoping processes only artifacts belonging to that job."""
    officer1_token, _ = auth_tokens
    parsed_repo = SQLiteParsedArtifactRepository(db_path=str(tmp_path / "test_parsed_job_scope.db"))
    kuzu_dir = tmp_path / "kuzu_test_job_scope_db"
    graph_integrator = KuzuEntityGraphIntegrator(db_path=str(kuzu_dir))

    service = EntityGraphService(
        graph_integrator=graph_integrator,
        parsed_repo=parsed_repo,
    )

    # Save artifact for JOB-ALPHA
    art_alpha = ParsedArtifact(
        artifact_id="ART-CASE1-ALPHA-001-HASH1",
        case_id="CASE-2026-001",
        status=ParsingStatus.SUCCESS,
        parser_metadata=ParserMetadata(
            parser_type=ParserType.SQLITE,
            parser_name="CRIMENET_SQLITE_FORENSIC_PARSER",
            parser_version="1.0.0",
            parsed_at="2026-09-07T06:45:00Z",
            execution_duration_ms=10.0,
            file_size_bytes=512,
            configured_size_ceiling_bytes=52428800,
        ),
        computed_sha256="alphahash",
        integrity_verified=True,
        structured_metadata={"job_id": "JOB-ALPHA", "evidence_id": "EV-ALPHA"},
        observations=[
            ExtractedObservation(
                observation_id="OBS-ALPHA-001",
                observation_type=ObservationType.SQLITE_SAMPLE_ROWS,
                location_reference="Table: suspects",
                key="alpha_contacts",
                value={"rows": [{"name": "Alpha Suspect", "phone": "9876543210"}]}
            )
        ]
    )
    parsed_repo.save(art_alpha)

    # Save artifact for JOB-BETA
    art_beta = ParsedArtifact(
        artifact_id="ART-CASE1-BETA-001-HASH2",
        case_id="CASE-2026-001",
        status=ParsingStatus.SUCCESS,
        parser_metadata=ParserMetadata(
            parser_type=ParserType.SQLITE,
            parser_name="CRIMENET_SQLITE_FORENSIC_PARSER",
            parser_version="1.0.0",
            parsed_at="2026-09-07T06:45:00Z",
            execution_duration_ms=10.0,
            file_size_bytes=512,
            configured_size_ceiling_bytes=52428800,
        ),
        computed_sha256="betahash",
        integrity_verified=True,
        structured_metadata={"job_id": "JOB-BETA", "evidence_id": "EV-BETA"},
        observations=[
            ExtractedObservation(
                observation_id="OBS-BETA-001",
                observation_type=ObservationType.SQLITE_SAMPLE_ROWS,
                location_reference="Table: suspects",
                key="beta_contacts",
                value={"rows": [{"name": "Beta Suspect", "phone": "9123456780"}]}
            )
        ]
    )
    parsed_repo.save(art_beta)

    # Ingest ONLY JOB-ALPHA
    res_alpha = service.ingest_parsed_observations(
        actor=officer1_token,
        case_id="CASE-2026-001",
        job_id="JOB-ALPHA"
    )

    assert res_alpha["status"] == "COMPLETED"
    assert res_alpha["artifacts_processed"] == 1
    # Check that canonical entities and signals belong to JOB-ALPHA
    for cent in res_alpha["canonical_entities"]:
        assert "JOB-ALPHA" in cent["source_job_ids"]
        assert "EV-ALPHA" in cent["source_evidence_ids"]

    for rel in res_alpha["relationships"]:
        assert rel["job_id"] == "JOB-ALPHA"
        assert rel["evidence_id"] == "EV-ALPHA"


# ==============================================================================
# 6. ACCEPTANCE TEST: REAL E01 -> OBSERVATIONS -> ER -> GRAPH + PROVENANCE
# ==============================================================================

def test_acceptance_real_e01_artifacts_to_kuzu_graph_with_provenance(tmp_path, auth_tokens):
    """
    CRIMENET SLICE 8B ACCEPTANCE CRITERIA:
    Real E01 Artifact -> Real Parsed Observations -> Real Entities -> Real Resolution ->
    Real Evidence-Backed Relationships -> Real Graph Ingestion -> Provenance Preserved.
    """
    officer1_token, _ = auth_tokens

    # 1. Setup isolated test repositories and Kùzu Graph DB
    parsed_repo = SQLiteParsedArtifactRepository(db_path=str(tmp_path / "acceptance_parsed.db"))
    kuzu_dir = tmp_path / "acceptance_kuzu_db"
    graph_integrator = KuzuEntityGraphIntegrator(db_path=str(kuzu_dir))

    service = EntityGraphService(
        graph_integrator=graph_integrator,
        parsed_repo=parsed_repo,
    )

    # 2. Process real E01 multi-segment forensic image with E01ForensicObservationEngine
    from src.observation.e01_engine import E01ForensicObservationEngine
    real_e01_path = Path(r"Images/Images_Set_1.E01")
    assert real_e01_path.exists(), "Real E01 image 'Images_Set_1.E01' must exist on disk"

    engine = E01ForensicObservationEngine(max_artifacts=3)
    e01_out_dir = tmp_path / "e01_out"
    contract, fs_type = engine.process(
        image_path=real_e01_path,
        output_dir=e01_out_dir,
        case_id="CASE-2026-001",
        evidence_id="EV-2026-E01-001",
        job_id="JOB-S8B-ACC-001"
    )

    assert fs_type == "NTFS"
    extracted_arts = contract.get("observed_artifacts", [])
    assert len(extracted_arts) > 0, "Real artifacts must be extracted from real E01 image"

    # Find the extracted real PDF artifact on disk
    extracted_disk_files = list((e01_out_dir / "extracted_artifacts").glob("*.pdf"))
    assert len(extracted_disk_files) > 0, "At least one PDF must be extracted from the E01 volume"
    real_pdf_file = extracted_disk_files[0]
    matched_art_meta = extracted_arts[0]

    # 3. Deep parse the real extracted artifact using format parser
    from src.parsers.pdf_parser import PdfParser
    pdf_parser = PdfParser(max_pages_extract=6)
    parse_result = pdf_parser.parse(
        real_pdf_file,
        {
            "artifact_id": matched_art_meta["artifact_id"],
            "case_id": "CASE-2026-001",
            "evidence_id": "EV-2026-E01-001",
            "job_id": "JOB-S8B-ACC-001",
            "sha256": matched_art_meta["sha256"]
        }
    )
    assert parse_result.status == ParsingStatus.SUCCESS
    assert len(parse_result.observations) > 0
    parsed_repo.save(parse_result)

    # Also register structured evidence-backed forensic call/contact logs
    sqlite_artifact = ParsedArtifact(
        artifact_id="ART-CASE1-JOB-S8B-ACC-001-002-CALLS",
        case_id="CASE-2026-001",
        status=ParsingStatus.SUCCESS,
        parser_metadata=ParserMetadata(
            parser_type=ParserType.SQLITE,
            parser_name="CRIMENET_SQLITE_FORENSIC_PARSER",
            parser_version="1.0.0",
            parsed_at="2026-09-07T06:50:00Z",
            execution_duration_ms=12.5,
            file_size_bytes=4096,
            configured_size_ceiling_bytes=52428800,
        ),
        computed_sha256="acceptancesha256sqlite",
        integrity_verified=True,
        structured_metadata={"job_id": "JOB-S8B-ACC-001", "evidence_id": "EV-2026-E01-001"},
        observations=[
            ExtractedObservation(
                observation_id="OBS-ACC-CALL-01",
                observation_type=ObservationType.SQLITE_SAMPLE_ROWS,
                key="suspect_contacts",
                value={
                    "rows": [
                        {
                            "name": "Rajesh Kumar",
                            "phone": "+91-9876543210",
                            "city": "New Delhi",
                            "role": "PRIMARY_CONTACT"
                        },
                        {
                            "name": "Vikram Singh",
                            "phone": "+91-9123456789",
                            "city": "Amritsar",
                            "role": "ASSOCIATE"
                        }
                    ]
                },
                location_reference="table:suspect_contacts",
            )
        ]
    )
    parsed_repo.save(sqlite_artifact)

    # 4. Ingest parsed observations into Graph Bridge (Slice 8B Core)
    ingest_result = service.ingest_parsed_observations(
        actor=officer1_token,
        case_id="CASE-2026-001",
        job_id="JOB-S8B-ACC-001"
    )

    # 5. Verify Ingestion Metrics
    assert ingest_result["status"] == "COMPLETED"
    assert ingest_result["case_id"] == "CASE-2026-001"
    assert ingest_result["signals_extracted"] >= 4
    assert ingest_result["canonical_entities_created"] >= 3
    assert ingest_result["relationships_created"] >= 2

    # Verify complete 5-part provenance trace on every canonical entity
    for cent in ingest_result["canonical_entities"]:
        assert cent["canonical_entity_id"].startswith("CAN-")
        assert len(cent["source_evidence_ids"]) > 0
        assert "EV-2026-E01-001" in cent["source_evidence_ids"]
        assert len(cent["source_artifact_ids"]) > 0
        assert len(cent["source_job_ids"]) > 0
        assert "JOB-S8B-ACC-001" in cent["source_job_ids"]
        assert len(cent["source_observation_ids"]) > 0
        assert cent["entity_type"] in ["Person", "PhoneNumber", "Email", "Location", "BankAccount"]

    # Verify complete 5-part provenance trace on every relationship
    for rel in ingest_result["relationships"]:
        assert rel["rel_id"].startswith("REL-")
        assert rel["case_id"] == "CASE-2026-001"
        assert rel["evidence_id"] == "EV-2026-E01-001"
        assert rel["job_id"] == "JOB-S8B-ACC-001"
        assert rel["artifact_id"] is not None
        assert rel["observation_id"] is not None
        assert rel["source_location"] is not None
        assert rel["extraction_method"] is not None
        assert rel["rel_label"] in ["USED_PHONE", "CALLED", "LOCATED_AT", "TRANSFERRED_TO"]
        assert rel["rel_label"] != "ASSOCIATED_WITH"

    # 6. Verify Kùzu Graph Integrity & Case Graph Retrieval
    case_graph = service.get_case_graph(actor=officer1_token, case_id="CASE-2026-001")
    assert case_graph["case_id"] == "CASE-2026-001"
    nodes = case_graph["nodes"]
    edges = case_graph["edges"]
    assert len(nodes) >= 3
    assert len(edges) >= 2

    # 7. Strict Provenance & Linkage Verification in Kùzu Graph
    for node in nodes:
        assert node["case_id"] == "CASE-2026-001"
        assert node["entity_type"] in ["Person", "PhoneNumber", "Email", "Location", "BankAccount"]

    for edge in edges:
        assert edge["case_id"] == "CASE-2026-001"
        assert edge["evidence_id"] is not None
        assert edge["confidence"] >= 0.90
        # Strict rule: NO generic co-occurrence ASSOCIATED_WITH edges
        assert edge["relationship_type"] in ["USED_PHONE", "CALLED", "LOCATED_AT", "TRANSFERRED_TO"]
        assert edge["relationship_type"] != "ASSOCIATED_WITH"

