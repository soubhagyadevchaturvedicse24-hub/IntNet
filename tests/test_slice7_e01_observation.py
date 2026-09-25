"""
Comprehensive Verification and Security Test Suite for CRIMENET Slice 7:
E01 Forensic Observation Engine & Process-Isolated Subprocess Worker.
Tests:
1. Real E01 + E02 segment discovery
2. Unified multi-segment media stream & boundary crossing
3. NTFS filesystem detection
4. Logical volume handling at offset 0
5. Full recursive directory traversal
6. Representative file extraction
7. Cryptographic SHA-256 verification of extracted artifacts
8. EvidenceContract_v1 generation & schema conformance
9. Pre/Post source evidence SHA-256 immutability assertion
10. Malformed / truncated E01 error handling
11. Missing companion segment (.E02) error handling
12. Subprocess worker timeout enforcement
13. Subprocess worker crash / failure isolation
14. Authorization & BOLA/BFLA protection
15. Path traversal defense
16. Artifact provenance integrity trace
17. Slice 6 Artifact Explorer integration
"""

import hashlib
import io
import json
import os
import shutil
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.auth.service import AuthService
from src.observation.e01_engine import E01ForensicObservationEngine
from src.observation.isolated_engine import IsolatedObservationEngine
from src.processing.models import JobStatus
from src.processing.service import ProcessingService

client = TestClient(app)
auth_service = AuthService()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REAL_E01_PATH = PROJECT_ROOT / "Images" / "Images_Set_1.E01"
if not REAL_E01_PATH.exists():
    for _fb in [Path(r"D:\Proto SIH\Chat gpt\Images\Images_Set_1.E01"), Path(r"D:\Proto SIH\Images\Images_Set_1.E01")]:
        if _fb.exists():
            REAL_E01_PATH = _fb
            break
REAL_E02_PATH = REAL_E01_PATH.with_name("Images_Set_1.E02")

KNOWN_SHA256_E01 = "733948eee283af8e0dc9c6e389039569a41c4522172e8cdfcebf34e86f1cd21a"
KNOWN_SHA256_E02 = "1da71529a72d2e10e060efe900616f098691c65787ada11c95cefed7f8e0f84d"


def get_token(username: str, password: str = "OfficerPass123!") -> str:
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


# ============================================================================
# 1. REAL MULTI-SEGMENT E01 OBSERVATION & PARSING TESTS
# ============================================================================

def test_real_e01_discovery_and_multi_segment_assembly(tmp_path):
    """Test 1 & 2: Discovers companion E02, creates unified media, reads across segment boundary."""
    engine = E01ForensicObservationEngine(max_artifacts=5)
    
    # Calculate pre-hash to verify immutability
    pre_e01_hash = engine.calculate_file_sha256(REAL_E01_PATH)
    pre_e02_hash = engine.calculate_file_sha256(REAL_E02_PATH)
    assert pre_e01_hash == KNOWN_SHA256_E01
    assert pre_e02_hash == KNOWN_SHA256_E02

    contract_v1, observed_fs = engine.process(
        image_path=REAL_E01_PATH,
        output_dir=tmp_path,
        case_id="CASE-2026-001",
        evidence_id="EV-E01-001",
        job_id="JOB-S7-TEST-001"
    )

    # Test 3 & 4: NTFS filesystem detected on logical volume
    assert observed_fs == "NTFS"
    src_ev = contract_v1["source_evidence"]
    assert src_ev["container_format"] == "E01"
    assert src_ev["observed_filesystem"] == "NTFS"
    assert src_ev["volume_system_detected"] is False  # Logical volume
    assert src_ev["filesystem_offset"] == 0
    assert len(src_ev["segment_filenames"]) == 2
    assert "Images_Set_1.E01" in src_ev["segment_filenames"]
    assert "Images_Set_1.E02" in src_ev["segment_filenames"]

    # Test 5: Full traversal counts
    assert src_ev["total_directories_discovered"] >= 1000
    assert src_ev["total_files_discovered"] >= 2500

    # Test 6 & 7: Representative extraction & SHA-256 calculation
    artifacts = contract_v1["observed_artifacts"]
    assert len(artifacts) == 5
    for art in artifacts:
        assert "artifact_id" in art
        assert "artifact_name" in art
        assert "sha256" in art
        assert len(art["sha256"]) == 64
        assert art["allocation_status"] in ["ALLOCATED", "DELETED"]
        assert art["provenance_trace"].startswith("Images_Set_1.E01:")

        # Verify extracted file actually exists on disk in extracted_artifacts/
        extracted_file = tmp_path / "extracted_artifacts" / Path(art["content_path"]).name
        assert extracted_file.exists()
        # Verify hash of extracted file matches reported hash
        assert hashlib.sha256(extracted_file.read_bytes()).hexdigest() == art["sha256"]

    # Test 8: EvidenceContract_v1 schema structure
    assert contract_v1["contract_version"] == "1.0.0"
    assert contract_v1["provenance_envelope"]["case_id"] == "CASE-2026-001"
    assert contract_v1["provenance_envelope"]["engine_name"] == "CRIMENET_E01_OBSERVATION_ENGINE"

    # Entities derived only from artifacts, not E01 container headers
    for ent in contract_v1.get("extracted_entities", []):
        assert ent["source_offset"].startswith("ART-")  # Must reference an observed artifact ID

    # Test 9: Source evidence SHA-256 immutability assertion
    post_e01_hash = engine.calculate_file_sha256(REAL_E01_PATH)
    post_e02_hash = engine.calculate_file_sha256(REAL_E02_PATH)
    assert post_e01_hash == pre_e01_hash
    assert post_e02_hash == pre_e02_hash


# ============================================================================
# 2. SUBPROCESS WORKER ISOLATION TESTS
# ============================================================================

def test_isolated_worker_execution(tmp_path):
    """Verifies that IsolatedObservationEngine runs cleanly in a standalone subprocess."""
    isolated_engine = IsolatedObservationEngine(timeout_seconds=60, max_artifacts=3)
    
    contract_v1, observed_fs = isolated_engine.process(
        image_path=REAL_E01_PATH,
        output_dir=tmp_path,
        case_id="CASE-2026-001",
        evidence_id="EV-E01-002",
        job_id="JOB-S7-ISOLATED"
    )

    assert observed_fs == "NTFS"
    assert len(contract_v1["observed_artifacts"]) == 3
    contract_file = tmp_path / "evidence_contract_JOB-S7-ISOLATED.json"
    assert contract_file.exists()


def test_isolated_worker_timeout_enforcement(tmp_path):
    """Test 12: Verifies that a worker exceeding max_runtime is terminated with TimeoutError."""
    # Set impossible 0.001s timeout to guarantee timeout
    short_timeout_engine = IsolatedObservationEngine(timeout_seconds=0.001, max_artifacts=5)
    
    with pytest.raises(TimeoutError) as exc_info:
        short_timeout_engine.process(
            image_path=REAL_E01_PATH,
            output_dir=tmp_path,
            case_id="CASE-2026-001",
            evidence_id="EV-E01-TIMEOUT",
            job_id="JOB-S7-TIMEOUT"
        )
    assert "WORKER TIMEOUT" in str(exc_info.value)


def test_isolated_worker_crash_containment(tmp_path):
    """Test 13: Verifies that a worker failure does not crash parent process."""
    isolated_engine = IsolatedObservationEngine(timeout_seconds=30)
    fake_path = tmp_path / "non_existent_image.E01"

    with pytest.raises(RuntimeError) as exc_info:
        isolated_engine.process(
            image_path=fake_path,
            output_dir=tmp_path,
            case_id="CASE-2026-001",
            evidence_id="EV-E01-FAIL",
            job_id="JOB-S7-FAIL"
        )
    assert "WORKER FAILURE" in str(exc_info.value)


# ============================================================================
# 3. ADVERSARIAL & SECURITY TESTS (UNTRUSTED INPUTS)
# ============================================================================

def test_malformed_truncated_e01_handling(tmp_path):
    """Test 10: Truncated E01 file (only 512 bytes) raises clean exception."""
    corrupt_e01 = tmp_path / "corrupt.E01"
    # Write corrupt header that has magic but no chunk tables
    corrupt_e01.write_bytes(b"EVF\t\r\n\xff\x00" + b"\x00" * 504)

    engine = E01ForensicObservationEngine()
    with pytest.raises(Exception) as exc_info:
        engine.process(
            image_path=corrupt_e01,
            output_dir=tmp_path / "out",
            case_id="CASE-2026-001",
            evidence_id="EV-CORRUPT",
            job_id="JOB-CORRUPT"
        )
    assert exc_info.value is not None


def test_fake_extension_rejected(tmp_path):
    """Test non-E01 file with .E01 extension is rejected cleanly by magic verification."""
    fake_e01 = tmp_path / "fake.E01"
    fake_e01.write_bytes(b"THIS IS NOT AN E01 FILE AT ALL!")

    engine = E01ForensicObservationEngine()
    with pytest.raises(ValueError) as exc_info:
        engine.process(
            image_path=fake_e01,
            output_dir=tmp_path / "out",
            case_id="CASE-2026-001",
            evidence_id="EV-FAKE",
            job_id="JOB-FAKE"
        )
    assert "Invalid forensic image format" in str(exc_info.value)


def test_path_traversal_defense(tmp_path):
    """Test 15: Malformed internal path attempting to escape sandbox is contained."""
    engine = E01ForensicObservationEngine()
    
    # Verify that destination paths resolve strictly within output_dir
    artifacts_dir = tmp_path / "extracted_artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    unsafe_filename = "../../etc/passwd"
    clean_name = E01ForensicObservationEngine.sanitize_artifact_filename(unsafe_filename)
    safe_target = (artifacts_dir / f"ART_TEST_{clean_name}").resolve()

    assert safe_target.is_relative_to(tmp_path.resolve())
    assert ".." not in safe_target.name
    assert "passwd" in safe_target.name


# ============================================================================
# 4. SLICE 6 ARTIFACT SERVICE INTEGRATION & BOLA SECURITY TESTS
# ============================================================================

def test_slice6_artifact_ingestion_and_explorer_api(tmp_path):
    """Test 16 & 17: Full pipeline from E01 observation to Slice 6 Artifact Explorer."""
    token = get_token("officer1")
    headers = {"Authorization": f"Bearer {token}"}

    # Run isolated observation engine to produce a real contract
    isolated_engine = IsolatedObservationEngine(timeout_seconds=60, max_artifacts=4)
    contract_v1, observed_fs = isolated_engine.process(
        image_path=REAL_E01_PATH,
        output_dir=tmp_path,
        case_id="CASE-2026-001",
        evidence_id="EV-E01-INGEST",
        job_id="JOB-S7-INGEST"
    )

    # Ingest contract directly via ArtifactService
    from src.api.artifact_routes import artifact_service
    from src.processing.models import ProcessingJob

    dummy_job = ProcessingJob(
        job_id="JOB-S7-INGEST",
        case_id="CASE-2026-001",
        evidence_id="EV-E01-INGEST",
        status=JobStatus.COMPLETED,
        engine_name=isolated_engine.get_engine_name(),
        engine_version=isolated_engine.get_engine_version(),
        image_format="E01",
        created_at=time.time(),
        requested_by="officer1",
        output_directory=str(tmp_path),
        pre_processing_sha256=KNOWN_SHA256_E01
    )

    ingested_artifacts = artifact_service.ingest_contract_artifacts(contract_v1, dummy_job)
    assert len(ingested_artifacts) == 4

    # Query via Case-Scoped Artifact Explorer REST API
    res = client.get("/api/v1/cases/CASE-2026-001/artifacts", headers=headers)
    assert res.status_code == 200
    api_artifacts = res.json()
    assert len(api_artifacts) >= 4

    first_art_id = ingested_artifacts[0].artifact_id
    res_art = client.get(f"/api/v1/cases/CASE-2026-001/artifacts/{first_art_id}", headers=headers)
    assert res_art.status_code == 200
    art_data = res_art.json()
    assert art_data["artifact_id"] == first_art_id
    assert art_data["category"] in ["DOCUMENT", "IMAGE", "DATABASE", "SPREADSHEET", "LOG", "OTHER"]
    assert art_data["path_within_source"].startswith("Images_Set_1.E01:")


def test_bola_unauthorized_case_artifact_access():
    """Test 14: Officer 2 cannot view artifacts belonging to Officer 1's case."""
    token2 = get_token("officer2")
    headers2 = {"Authorization": f"Bearer {token2}"}

    # Officer 2 accessing Officer 1's case artifacts
    res = client.get("/api/v1/cases/CASE-2026-001/artifacts", headers=headers2)
    assert res.status_code == 403
    assert "DENY" in res.json()["detail"]


def test_missing_e02_companion_segment_handled_gracefully(tmp_path):
    """Test 11: Missing continuation segment raises clean exception without crashing."""
    # Create a directory containing only E01 (without companion E02)
    only_e01 = tmp_path / "Images_Set_1.E01"
    # Copy first 1MB of E01
    with open(REAL_E01_PATH, "rb") as src, open(only_e01, "wb") as dst:
        dst.write(src.read(1024 * 1024))

    engine = E01ForensicObservationEngine()
    with pytest.raises(Exception) as exc_info:
        engine.process(
            image_path=only_e01,
            output_dir=tmp_path / "out",
            case_id="CASE-2026-001",
            evidence_id="EV-E01-SINGLE",
            job_id="JOB-MISSING-E02"
        )
    assert exc_info.value is not None
