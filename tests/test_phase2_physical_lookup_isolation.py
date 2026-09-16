"""
Targeted tests for Phase 2: Case-scoped physical artifact lookup isolation.
Ensures that _find_physical_artifact never searches or returns files from other cases' directories.
"""

import hashlib
import pytest
from pathlib import Path
from src.artifacts.models import Artifact, ArtifactCategory, AllocationStatus, RecoveryStatus, ViewerType, ProvenanceEnvelope
from src.artifacts.service import ArtifactService


def test_physical_artifact_lookup_strictly_case_isolated(tmp_path):
    """
    Verifies that an artifact in CASE-A will never resolve to a physical extracted file
    belonging to CASE-B, even if they have identical hashes and filenames.
    """
    proc_output = tmp_path / "processing_output"
    case_a_dir = proc_output / "CASE-2026-001"
    case_b_dir = proc_output / "CASE-2026-002"
    case_a_dir.mkdir(parents=True)
    case_b_dir.mkdir(parents=True)

    # Place a secret physical file inside CASE-B extracted_artifacts
    case_b_extracted = case_b_dir / "JOB-CASE2-001" / "extracted_artifacts"
    case_b_extracted.mkdir(parents=True)
    case_b_file = case_b_extracted / "confidential_file.pdf"
    file_bytes = b"%PDF-1.4 confidential data for Case B only"
    case_b_file.write_bytes(file_bytes)
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    service = ArtifactService(storage_base_dir=str(proc_output))

    # Construct Artifact belonging to CASE-A with same hash and filename
    prov_a = ProvenanceEnvelope(
        case_id="CASE-2026-001",
        evidence_id="EV-A",
        processing_job_id="JOB-CASE1-001",
        engine_name="CRIMENET_E01_OBSERVATION_ENGINE",
        engine_version="1.0.0",
        source_reference="EV-A",
        observation_reference="confidential_file.pdf"
    )

    art_a = Artifact(
        artifact_id="ART-2026-001-TEST-001",
        case_id="CASE-2026-001",
        evidence_id="EV-A",
        processing_job_id="JOB-CASE1-001",
        filename="confidential_file.pdf",
        path_within_source="/confidential_file.pdf",
        category=ArtifactCategory.DOCUMENT,
        mime_type="application/pdf",
        file_extension=".pdf",
        size_bytes=len(file_bytes),
        sha256=sha256_hash,
        allocation_status=AllocationStatus.ALLOCATED,
        recovery_status=RecoveryStatus.NONE,
        observation_method="FILE_SYSTEM_PARSE",
        recommended_viewer=ViewerType.PDF,
        provenance_chain=prov_a,
        content_reference="CASE-2026-001/JOB-CASE1-001/confidential_file.pdf"
    )

    # Call _find_physical_artifact for CASE-A
    found = service._find_physical_artifact(art_a, art_a.content_reference)

    # Must NOT find CASE-B's file
    assert found is None or not str(found).startswith(str(case_b_dir)), (
        f"SECURITY BREACH: CASE-A lookup accessed file belonging to CASE-B: {found}"
    )
    assert found is None
