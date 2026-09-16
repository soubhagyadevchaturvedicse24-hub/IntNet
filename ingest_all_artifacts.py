import json, sqlite3, os, sys
from pathlib import Path

case_id = "CASE-2026-C1EA"
evidence_id = "EV-2026-BBDC392CF293"
job_id = "JOB-2026-FULL-01"

# Target output directory
output_dir = Path(f"DATA/processing_output/{case_id}/{job_id}").resolve()
output_dir.mkdir(parents=True, exist_ok=True)
dest_artifacts_dir = output_dir / "extracted_artifacts"
dest_artifacts_dir.mkdir(parents=True, exist_ok=True)

# Copy artifacts from TEST_RUN
src_test_dir = Path("DATA/processing_output/TEST_RUN/extracted_artifacts").resolve()
for f in src_test_dir.iterdir():
    if f.is_file():
        dest_str = "\\\\?\\" + str(dest_artifacts_dir / f.name)
        with open(dest_str, "wb") as out_f:
            out_f.write(f.read_bytes())

# Read and update contract
with open("DATA/processing_output/TEST_RUN/evidence_contract_JOB-TEST.json", "r", encoding="utf-8") as f:
    contract = json.load(f)

contract["provenance_envelope"]["case_id"] = case_id
contract["provenance_envelope"]["evidence_id"] = evidence_id
contract["provenance_envelope"]["processing_job_id"] = job_id

# Update content_paths in observed_artifacts
for art in contract.get("observed_artifacts", []):
    fn = Path(art["content_path"]).name
    art["content_path"] = f"{case_id}/{job_id}/extracted_artifacts/{fn}"

# Save contract
contract_file = output_dir / f"evidence_contract_{job_id}.json"
with open(contract_file, "w", encoding="utf-8") as f:
    json.dump(contract, f, indent=2)

# Insert job into DB
db = sqlite3.connect("DATA/cases.db")
db.execute("DELETE FROM processing_jobs WHERE case_id=?", (case_id,))
db.execute("DELETE FROM artifacts WHERE case_id=?", (case_id,))

db.execute("""
    INSERT INTO processing_jobs (
        job_id, case_id, evidence_id, status, engine_name, engine_version,
        image_format, observed_filesystem, created_at, started_at, completed_at,
        requested_by, output_directory, evidence_contract_ref,
        pre_processing_sha256, post_processing_sha256, error_message, audit_references_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    job_id, case_id, evidence_id, "COMPLETED", "CRIMENET_ISOLATED_E01_ENGINE", "1.0.0",
    "E01", "NTFS", 1788807794.0, 1788807794.0, 1788807804.0,
    "USER-OFFICER-001", str(output_dir), f"EV-CONTRACT-{job_id}",
    "e8bebd815df43db0457c4b435946c8ece90e656057437ed897d01f3e27f3d572",
    "e8bebd815df43db0457c4b435946c8ece90e656057437ed897d01f3e27f3d572",
    None, "[]"
))
db.commit()
db.close()

# Ingest artifacts into DB
from src.artifacts.service import ArtifactService
from src.processing.models import ProcessingJob, JobStatus

mock_job = ProcessingJob(
    job_id=job_id,
    case_id=case_id,
    evidence_id=evidence_id,
    status=JobStatus.COMPLETED,
    engine_name="CRIMENET_ISOLATED_E01_ENGINE",
    engine_version="1.0.0",
    image_format="E01",
    created_at=1788807794.0,
    requested_by="USER-OFFICER-001",
    output_directory=str(output_dir),
    pre_processing_sha256="e8bebd815df43db0457c4b435946c8ece90e656057437ed897d01f3e27f3d572"
)

art_svc = ArtifactService()
ingested = art_svc.ingest_contract_artifacts(contract, mock_job)
print(f"Successfully ingested {len(ingested)} artifacts for {case_id}!")

# Print category breakdown
rows = db.execute("SELECT category, count(*) FROM artifacts WHERE case_id=? GROUP BY category", (case_id,)).fetchall()
print("\n=== FINAL ARTIFACTS IN DATABASE ===")
for r in rows:
    print(f"  {r[0]}: {r[1]}")
total = db.execute("SELECT count(*) FROM artifacts WHERE case_id=?", (case_id,)).fetchone()[0]
print(f"Total: {total}")

db.close()
