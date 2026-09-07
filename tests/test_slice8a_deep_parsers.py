"""
Automated Test Battery for CRIMENET Slice 8A — Deep Artifact Parsing & Evidence Enrichment.
Verifies PDF, Image, and SQLite parsers, magic byte defenses, BOLA enforcement,
bounded reading, crash isolation, cryptographic immutability, and real E01 artifact parsing.
"""

import hashlib
import io
import os
import sys
import sqlite3
import pytest
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image

from src.auth.models import TokenPayload, UserRole
from src.auth.service import AuthService
from src.artifacts.models import Artifact, ArtifactCategory, AllocationStatus, RecoveryStatus, ViewerType, ProvenanceEnvelope
from src.artifacts.repository import SQLiteArtifactRepository
from src.artifacts.service import ArtifactService
from src.parsers.models import ParsingStatus, ParserType, ObservationType
from src.parsers.base import ArtifactParser
from src.parsers.pdf_parser import PdfParser
from src.parsers.image_parser import ImageParser
from src.parsers.sqlite_parser import SqliteParser
from src.parsers.registry import ParserRegistry
from src.parsers.repository import SQLiteParsedArtifactRepository
from src.parsers.service import DeepParsingService


# Fixture directories
DATA_DIR = Path("DATA")
FIXTURES_DIR = DATA_DIR / "test_fixtures"
REAL_EXTRACTED_DIR = DATA_DIR / "processing_output" / "CASE-2026-001" / "JOB-2026-752377" / "extracted_artifacts"


@pytest.fixture(scope="module")
def setup_test_files():
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Synthetic SQLite Database (SYNTHETIC TEST DATA)
    sqlite_path = FIXTURES_DIR / "synthetic_sample.db"
    if not sqlite_path.exists():
        conn = sqlite3.connect(str(sqlite_path))
        cur = conn.cursor()
        cur.execute("CREATE TABLE suspect_contacts (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, role TEXT);")
        for i in range(1, 26):
            cur.execute("INSERT INTO suspect_contacts VALUES (?, ?, ?, ?)", (i, f"Contact {i}", f"+91-98765432{i:02d}", "COURIER"))
        conn.commit()
        conn.close()

    # 2. Minimal valid Image
    img_path = FIXTURES_DIR / "test_valid.png"
    img = Image.new("RGB", (64, 48), color="red")
    img.save(str(img_path))

    # 3. Spoofed files
    fake_pdf = FIXTURES_DIR / "spoofed_fake.pdf"
    fake_pdf.write_bytes(b"THIS IS NOT A VALID PDF HEADER AT ALL")

    fake_png = FIXTURES_DIR / "spoofed_fake.png"
    fake_png.write_bytes(b"PLAIN TEXT IN DISGUISE AS PNG")

    fake_db = FIXTURES_DIR / "spoofed_fake.db"
    fake_db.write_bytes(b"CORRUPT DATA NOT SQLITE HEADER")

    # 4. Corrupted format file
    corrupt_pdf = FIXTURES_DIR / "corrupt.pdf"
    corrupt_pdf.write_bytes(b"%PDF-1.4\n%TrUnCaTeD CoRrUpT BiNaRy")

    # 5. Unsupported file
    unsupported_file = FIXTURES_DIR / "test_data.xyz"
    unsupported_file.write_bytes(b"BINARY_PAYLOAD_UNSUPPORTED_TYPE_XYZ_12345")

    yield


import time

@pytest.fixture
def auth_tokens():
    officer_token = TokenPayload(
        sub="USER-OFFICER-001",
        username="officer1",
        role=UserRole.INVESTIGATION_OFFICER,
        exp=int(time.time()) + 3600,
        jti="test-jti-1"
    )
    unauthorized_officer = TokenPayload(
        sub="USER-OFFICER-002",
        username="officer2",
        role=UserRole.INVESTIGATION_OFFICER,
        exp=int(time.time()) + 3600,
        jti="test-jti-2"
    )
    return officer_token, unauthorized_officer


# ==============================================================================
# 1. PARSER CORE UNIT TESTS
# ==============================================================================

def test_pdf_parser_valid(setup_test_files):
    """Test 1: PDF parser extracts pages, metadata, and bounded text from valid PDF."""
    real_pdf = REAL_EXTRACTED_DIR / "ART_JOB-2026-752377_014_Crime_Linkage_Detector_Meeting_Minutes.pdf"
    assert real_pdf.exists(), "Sample PDF missing"

    parser = PdfParser()
    res = parser.parse(real_pdf, {"artifact_id": "ART-TEST-PDF", "case_id": "CASE-2026-001"})

    assert res.status == ParsingStatus.SUCCESS
    assert res.parser_metadata.parser_type == ParserType.PDF
    assert res.structured_metadata["total_pages"] >= 1
    assert res.integrity_verified is True
    assert len(res.observations) > 0
    # Text observation with page-level provenance
    text_obs = [o for o in res.observations if o.observation_type == ObservationType.DOCUMENT_TEXT]
    assert len(text_obs) >= 1
    assert "Page 1" in text_obs[0].location_reference


def test_image_parser_valid(setup_test_files):
    """Test 2: Image parser extracts dimensions, format, and EXIF from valid image."""
    img_path = FIXTURES_DIR / "test_valid.png"
    parser = ImageParser()
    res = parser.parse(img_path, {"artifact_id": "ART-TEST-IMG", "case_id": "CASE-2026-001"})

    assert res.status == ParsingStatus.SUCCESS
    assert res.parser_metadata.parser_type == ParserType.IMAGE
    assert res.structured_metadata["width"] == 64
    assert res.structured_metadata["height"] == 48
    assert res.structured_metadata["format"] == "PNG"


def test_sqlite_parser_valid(setup_test_files):
    """Test 3: SQLite parser extracts tables, columns, counts, and bounded sample rows."""
    db_path = FIXTURES_DIR / "synthetic_sample.db"
    parser = SqliteParser(sample_row_limit=10)
    res = parser.parse(db_path, {"artifact_id": "ART-TEST-DB", "case_id": "CASE-2026-001"})

    assert res.status == ParsingStatus.SUCCESS
    assert res.parser_metadata.parser_type == ParserType.SQLITE
    assert "suspect_contacts" in res.structured_metadata["table_names"]
    table_meta = res.structured_metadata["tables"]["suspect_contacts"]
    assert table_meta["column_count"] == 4
    # Check bounded sample rows
    assert len(table_meta["sample_rows"]) == 10


# ==============================================================================
# 2. MAGIC BYTE SPOOFING & FORMAT SECURITY DEFENSES
# ==============================================================================

def test_magic_byte_rejects_spoofed_pdf(setup_test_files):
    """Test 4: Magic byte validation rejects file with .pdf extension containing non-PDF bytes."""
    fake_pdf = FIXTURES_DIR / "spoofed_fake.pdf"
    parser = PdfParser()
    res = parser.parse(fake_pdf, {"artifact_id": "ART-SPOOF-PDF", "case_id": "CASE-2026-001"})
    assert res.status == ParsingStatus.UNSUPPORTED


def test_magic_byte_rejects_spoofed_image(setup_test_files):
    """Test 5: Magic byte validation rejects file with .png extension containing non-image bytes."""
    fake_png = FIXTURES_DIR / "spoofed_fake.png"
    parser = ImageParser()
    res = parser.parse(fake_png, {"artifact_id": "ART-SPOOF-PNG", "case_id": "CASE-2026-001"})
    assert res.status == ParsingStatus.UNSUPPORTED


def test_magic_byte_rejects_spoofed_sqlite(setup_test_files):
    """Test 6: Magic byte validation rejects file with .db extension containing non-SQLite bytes."""
    fake_db = FIXTURES_DIR / "spoofed_fake.db"
    parser = SqliteParser()
    res = parser.parse(fake_db, {"artifact_id": "ART-SPOOF-DB", "case_id": "CASE-2026-001"})
    assert res.status == ParsingStatus.UNSUPPORTED


def test_unsupported_file_types(setup_test_files):
    """Test 7: Unsupported file types return status UNSUPPORTED cleanly without crashing."""
    unsupported_file = FIXTURES_DIR / "test_data.xyz"
    registry = ParserRegistry()
    parser = registry.get_parser_for_file(unsupported_file)
    res = parser.parse(unsupported_file, {"artifact_id": "ART-XYZ", "case_id": "CASE-2026-001"})
    assert res.status == ParsingStatus.UNSUPPORTED
    assert res.parser_metadata.parser_type == ParserType.UNSUPPORTED


def test_corrupt_malformed_handling(setup_test_files):
    """Test 8: Malformed/corrupt PDF handled gracefully returning status CORRUPTED or FAILED."""
    corrupt_pdf = FIXTURES_DIR / "corrupt.pdf"
    parser = PdfParser()
    res = parser.parse(corrupt_pdf, {"artifact_id": "ART-CORRUPT", "case_id": "CASE-2026-001"})
    # Must not raise unhandled exception; must report error state gracefully
    assert res.status in [ParsingStatus.CORRUPTED, ParsingStatus.FAILED]
    assert res.error_message is not None


def test_oversized_artifact_protection(setup_test_files):
    """Test 9: Oversized artifact protection enforces configured size limit (OVERSIZED)."""
    img_path = FIXTURES_DIR / "test_valid.png"
    # Set artificial tiny ceiling of 10 bytes to trigger constraint
    parser = ImageParser(max_file_size_bytes=10)
    res = parser.parse(img_path, {"artifact_id": "ART-OVERSIZED", "case_id": "CASE-2026-001"})
    assert res.status == ParsingStatus.OVERSIZED
    assert "exceeds configured prototype ceiling" in res.error_message


# ==============================================================================
# 3. BOLA / AUTHORIZATION / ACCESS CONTROL DEFENSES
# ==============================================================================

def test_bola_defense_cross_case_parse_denied(auth_tokens, setup_test_files):
    """Test 10: BOLA defense: cross-case parse request is rejected (PermissionError)."""
    officer_token, unauthorized_officer = auth_tokens

    # Register artifact under CASE-2026-001
    art_repo = SQLiteArtifactRepository(db_path="DATA/test_artifacts.db")
    service = DeepParsingService(
        artifact_service=ArtifactService(repository=art_repo),
        repository=SQLiteParsedArtifactRepository(db_path="DATA/test_parsed.db")
    )

    prov = ProvenanceEnvelope(
        case_id="CASE-2026-001",
        evidence_id="EV-001",
        processing_job_id="JOB-001",
        engine_name="CRIMENET_E01",
        engine_version="1.0",
        source_reference="img.E01",
        observation_reference="part0"
    )
    art = Artifact(
        artifact_id="ART-BOLA-001",
        case_id="CASE-2026-001",
        evidence_id="EV-001",
        processing_job_id="JOB-001",
        filename="test.png",
        path_within_source="/test.png",
        provenance_chain=prov,
        content_reference="test_fixtures/test_valid.png"
    )
    art_repo.save(art)

    # Unauthorized officer (only authorized for CASE-2026-999) attempts to parse CASE-2026-001 artifact
    with pytest.raises(PermissionError):
        service.parse_artifact(
            actor=unauthorized_officer,
            case_id="CASE-2026-001",
            artifact_id="ART-BOLA-001"
        )


def test_id_manipulation_defense(auth_tokens, setup_test_files):
    """Test 11: Cross-case ID manipulation defense: artifact belonging to another case rejected."""
    officer_token, _ = auth_tokens
    art_repo = SQLiteArtifactRepository(db_path="DATA/test_artifacts.db")
    service = DeepParsingService(
        artifact_service=ArtifactService(repository=art_repo),
        repository=SQLiteParsedArtifactRepository(db_path="DATA/test_parsed.db")
    )

    # Request artifact ART-BOLA-001 under mismatched URL case_id 'CASE-2026-002'
    with pytest.raises(PermissionError) as exc_info:
        service.parse_artifact(
            actor=officer_token,
            case_id="CASE-2026-002",
            artifact_id="ART-BOLA-001"
        )
    assert "ID MANIPULATION" in str(exc_info.value)


def test_path_traversal_defense(auth_tokens):
    """Test 12: Path traversal injection in artifact content reference is rejected."""
    officer_token, _ = auth_tokens
    art_repo = SQLiteArtifactRepository(db_path="DATA/test_artifacts.db")
    service = DeepParsingService(
        artifact_service=ArtifactService(repository=art_repo),
        repository=SQLiteParsedArtifactRepository(db_path="DATA/test_parsed.db")
    )

    prov = ProvenanceEnvelope(
        case_id="CASE-2026-001",
        evidence_id="EV-001",
        processing_job_id="JOB-001",
        engine_name="CRIMENET_E01",
        engine_version="1.0",
        source_reference="img.E01",
        observation_reference="part0"
    )
    traversal_art = Artifact(
        artifact_id="ART-TRAVERSAL-001",
        case_id="CASE-2026-001",
        evidence_id="EV-001",
        processing_job_id="JOB-001",
        filename="traversal.png",
        path_within_source="/etc/passwd",
        provenance_chain=prov,
        content_reference="../../Windows/System32/calc.exe"
    )
    art_repo.save(traversal_art)

    with pytest.raises(PermissionError) as exc_info:
        service.parse_artifact(
            actor=officer_token,
            case_id="CASE-2026-001",
            artifact_id="ART-TRAVERSAL-001"
        )
    assert "PATH TRAVERSAL" in str(exc_info.value)


# ==============================================================================
# 4. FORENSIC INTEGRITY & BOUNDED RESOURCE TESTS
# ==============================================================================

def test_cryptographic_integrity_verified(setup_test_files):
    """Test 13: Cryptographic integrity: recomputed SHA-256 matches preserved artifact SHA-256."""
    img_path = FIXTURES_DIR / "test_valid.png"
    actual_hash = hashlib.sha256(img_path.read_bytes()).hexdigest()

    parser = ImageParser()
    # Correct hash provided
    res_valid = parser.parse(img_path, {"artifact_id": "ART-HASH-1", "case_id": "CASE-1", "sha256": actual_hash})
    assert res_valid.integrity_verified is True
    assert res_valid.computed_sha256 == actual_hash

    # Tampered/wrong hash provided
    res_invalid = parser.parse(img_path, {"artifact_id": "ART-HASH-2", "case_id": "CASE-1", "sha256": "0000000000000000000000000000000000000000000000000000000000000000"})
    assert res_invalid.integrity_verified is False


def test_bounded_reads_sqlite_rows(setup_test_files):
    """Test 14: Bounded read defense: SQLite table with 25 rows strictly returns 10 sample records."""
    db_path = FIXTURES_DIR / "synthetic_sample.db"
    parser = SqliteParser(sample_row_limit=10, max_count_threshold=100)
    res = parser.parse(db_path, {"artifact_id": "ART-BOUNDS", "case_id": "CASE-1"})

    table_data = res.structured_metadata["tables"]["suspect_contacts"]
    assert table_data["sample_row_count"] == 10
    assert len(table_data["sample_rows"]) == 10
    # Provenance note must document bounded read
    sample_obs = [o for o in res.observations if o.observation_type == ObservationType.SQLITE_SAMPLE_ROWS][0]
    assert "LIMIT 10" in sample_obs.provenance_note


# ==============================================================================
# 5. REAL EVIDENCE ARTIFACT PARSING (IMAGES_SET_1.E01)
# ==============================================================================

def test_real_pdf_artifact_from_e01():
    """Test 15: Successfully parses real extracted PDF from Images_Set_1.E01 (Jeevan Setu.pdf)."""
    real_pdf = REAL_EXTRACTED_DIR / "ART_JOB-2026-752377_018_Jeevan_Setu.pdf"
    assert real_pdf.exists(), f"Real PDF missing at: {real_pdf}"

    parser = PdfParser(max_pages_extract=5)
    res = parser.parse(
        real_pdf,
        {
            "artifact_id": "ART-2026-001-1E6EA53D",
            "case_id": "CASE-2026-001",
            "sha256": "1e6ea53d82f0e8aa2e6122fd5f3d2038757b5fc88d8dd6a1a8cba93f020d18c1"
        }
    )

    assert res.status == ParsingStatus.SUCCESS
    assert res.integrity_verified is True
    assert res.structured_metadata["total_pages"] > 0
    assert res.structured_metadata["pages_inspected"] <= 5
    assert len(res.observations) > 0


def test_real_image_artifact_from_e01():
    """Test 16: Successfully parses real extracted PNG from Images_Set_1.E01 (Golden Temple Aarti Ceremony.png)."""
    real_img = REAL_EXTRACTED_DIR / "ART_JOB-2026-752377_015_Golden_Temple_Aarti_Ceremony.png"
    assert real_img.exists(), f"Real Image missing at: {real_img}"

    parser = ImageParser()
    res = parser.parse(
        real_img,
        {
            "artifact_id": "ART-2026-001-48A024E4",
            "case_id": "CASE-2026-001",
            "sha256": "48a024e4dfe86684220dead8af15cee9251082094eafac295e7e1450682ca5e2"
        }
    )

    assert res.status == ParsingStatus.SUCCESS
    assert res.integrity_verified is True
    assert res.structured_metadata["width"] > 0
    assert res.structured_metadata["height"] > 0
    assert res.structured_metadata["format"] == "PNG"


# ==============================================================================
# 6. REST API ENDPOINT INTEGRATION TESTS
# ==============================================================================

from fastapi.testclient import TestClient
from src.api.main import app

api_client = TestClient(app)


def test_api_parse_and_get_endpoints():
    """Test 17: Validates POST /parse and GET /parsed REST endpoints via FastAPI TestClient."""
    # Login as officer1
    login_res = api_client.post("/api/v1/auth/login", json={"username": "officer1", "password": "OfficerPass123!"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # First get list of artifacts in CASE-2026-001
    arts_res = api_client.get("/api/v1/cases/CASE-2026-001/artifacts", headers=headers)
    assert arts_res.status_code == 200
    artifacts = arts_res.json()
    assert len(artifacts) > 0

    target_art = artifacts[0]
    art_id = target_art["artifact_id"]

    # Trigger parse
    parse_res = api_client.post(f"/api/v1/cases/CASE-2026-001/artifacts/{art_id}/parse", headers=headers)
    assert parse_res.status_code == 200
    parsed_data = parse_res.json()
    assert parsed_data["artifact_id"] == art_id
    assert parsed_data["status"] in ["SUCCESS", "UNSUPPORTED"]

    # Retrieve parsed observations
    get_res = api_client.get(f"/api/v1/cases/CASE-2026-001/artifacts/{art_id}/parsed", headers=headers)
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert retrieved["artifact_id"] == art_id
    assert retrieved["computed_sha256"] == parsed_data["computed_sha256"]


def test_api_cross_case_bola_denial():
    """Test 18: Validates BOLA denial when accessing artifact from another case via API."""
    # Login as officer2 (authorized for CASE-2026-002 only)
    login_res = api_client.post("/api/v1/auth/login", json={"username": "officer2", "password": "OfficerPass456!"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to parse CASE-2026-001 artifact
    res = api_client.post("/api/v1/cases/CASE-2026-001/artifacts/ART-2026-001-1E6EA53D/parse", headers=headers)
    assert res.status_code == 403

