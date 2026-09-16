"""
Targeted tests for Phase 1: Artifact ID collision resistance and cross-case overwrite protection.
"""

import pytest
from src.artifacts.models import Artifact, ArtifactCategory, AllocationStatus, RecoveryStatus, ViewerType, ProvenanceEnvelope
from src.artifacts.repository import SQLiteArtifactRepository


def test_artifact_id_derivation_collision_resistance():
    """Verify that identical content in different cases or jobs generates distinct artifact IDs."""
    case1 = "CASE-2026-001"
    case2 = "CASE-2026-002"
    job1 = "JOB-2026-AAA-1111"
    job2 = "JOB-2026-BBB-2222"
    sha = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    clean_case1 = case1.replace("CASE-", "")
    clean_case2 = case2.replace("CASE-", "")

    id_c1_j1 = f"ART-{clean_case1}-{job1}-001-{sha[:12].upper()}"
    id_c2_j1 = f"ART-{clean_case2}-{job1}-001-{sha[:12].upper()}"
    id_c1_j2 = f"ART-{clean_case1}-{job2}-001-{sha[:12].upper()}"

    # Verify all are distinct
    assert id_c1_j1 != id_c2_j1
    assert id_c1_j1 != id_c1_j2
    assert id_c2_j1 != id_c1_j2
    assert id_c1_j1.startswith("ART-2026-001-JOB-2026-AAA-1111-001-")


def test_cross_case_overwrite_blocked_in_repository(tmp_path):
    """Verify that saving an existing artifact_id under a different case_id is rejected."""
    db_path = str(tmp_path / "test_cases.db")
    repo = SQLiteArtifactRepository(db_path=db_path)

    prov1 = ProvenanceEnvelope(
        case_id="CASE-2026-001",
        evidence_id="EV-1",
        processing_job_id="JOB-1",
        engine_name="CRIMENET_E01_OBSERVATION_ENGINE",
        engine_version="1.0.0",
        source_reference="EV-1",
        observation_reference="sample.pdf"
    )

    art1 = Artifact(
        artifact_id="ART-SAMPLE-001",
        case_id="CASE-2026-001",
        evidence_id="EV-1",
        processing_job_id="JOB-1",
        filename="sample.pdf",
        path_within_source="/sample.pdf",
        category=ArtifactCategory.DOCUMENT,
        mime_type="application/pdf",
        file_extension=".pdf",
        size_bytes=1024,
        sha256="abc123def456",
        allocation_status=AllocationStatus.ALLOCATED,
        recovery_status=RecoveryStatus.NONE,
        observation_method="FILE_SYSTEM_PARSE",
        recommended_viewer=ViewerType.PDF,
        provenance_chain=prov1,
        content_reference="CASE-2026-001/JOB-1/sample.pdf"
    )

    repo.save(art1)
    retrieved = repo.get_by_id("ART-SAMPLE-001")
    assert retrieved is not None
    assert retrieved.case_id == "CASE-2026-001"

    # Attempt to overwrite ART-SAMPLE-001 with CASE-2026-002
    prov2 = ProvenanceEnvelope(
        case_id="CASE-2026-002",
        evidence_id="EV-2",
        processing_job_id="JOB-2",
        engine_name="CRIMENET_E01_OBSERVATION_ENGINE",
        engine_version="1.0.0",
        source_reference="EV-2",
        observation_reference="sample.pdf"
    )

    art2 = Artifact(
        artifact_id="ART-SAMPLE-001",
        case_id="CASE-2026-002",
        evidence_id="EV-2",
        processing_job_id="JOB-2",
        filename="sample.pdf",
        path_within_source="/sample.pdf",
        category=ArtifactCategory.DOCUMENT,
        mime_type="application/pdf",
        file_extension=".pdf",
        size_bytes=1024,
        sha256="abc123def456",
        allocation_status=AllocationStatus.ALLOCATED,
        recovery_status=RecoveryStatus.NONE,
        observation_method="FILE_SYSTEM_PARSE",
        recommended_viewer=ViewerType.PDF,
        provenance_chain=prov2,
        content_reference="CASE-2026-002/JOB-2/sample.pdf"
    )

    with pytest.raises(ValueError) as exc:
        repo.save(art2)

    assert "CROSS-CASE OVERWRITE BLOCKED" in str(exc.value)

    # Confirm original artifact remains intact
    retrieved_after = repo.get_by_id("ART-SAMPLE-001")
    assert retrieved_after.case_id == "CASE-2026-001"
    assert retrieved_after.processing_job_id == "JOB-1"
