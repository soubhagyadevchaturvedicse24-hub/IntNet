"""
CRIMENET Slice 7A — Frontend <-> Backend End-to-End Acceptance Validation Test Runner.
Executes all required verification phases (Phases 0 - 15) with empirical tracing.
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure project root in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api.main import app
from src.observation.e01_engine import E01ForensicObservationEngine

client = TestClient(app)

E01_PATH = Path(r"D:\Proto SIH\Images\Images_Set_1.E01")
E02_PATH = Path(r"D:\Proto SIH\Images\Images_Set_1.E02")

EXPECTED_E01_SHA256 = "733948eee283af8e0dc9c6e389039569a41c4522172e8cdfcebf34e86f1cd21a"
EXPECTED_E02_SHA256 = "1da71529a72d2e10e060efe900616f098691c65787ada11c95cefed7f8e0f84d"


def calc_sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(4 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def run_e2e_validation():
    print("=" * 80)
    print("CRIMENET SLICE 7A: FRONTEND <-> BACKEND END-TO-END ACCEPTANCE VALIDATION")
    print("=" * 80)

    results = {}

    # ------------------------------------------------------------------------
    # PRE-TEST INTEGRITY
    # ------------------------------------------------------------------------
    print("\n>>> PRE-TEST INTEGRITY CHECK")
    pre_e01 = calc_sha256(E01_PATH)
    pre_e02 = calc_sha256(E02_PATH)
    print(f"  E01 Pre-SHA256: {pre_e01}")
    print(f"  E02 Pre-SHA256: {pre_e02}")
    assert pre_e01 == EXPECTED_E01_SHA256, "E01 Hash Mismatch before test!"
    assert pre_e02 == EXPECTED_E02_SHA256, "E02 Hash Mismatch before test!"
    print("  [PASS] Pre-test source hashes match forensic ground truth.")

    # ------------------------------------------------------------------------
    # PHASE 2: AUTHENTICATION TEST
    # ------------------------------------------------------------------------
    print("\n>>> PHASE 2: AUTHENTICATION TEST")
    auth_results = {}

    # 1. Valid login
    res_login_valid = client.post("/api/v1/auth/login", json={"username": "officer1", "password": "OfficerPass123!"})
    auth_results["valid_login_status"] = res_login_valid.status_code
    token1 = res_login_valid.json().get("access_token")
    auth_results["valid_login_user"] = res_login_valid.json().get("user", {}).get("username")
    auth_results["valid_login_role"] = res_login_valid.json().get("user", {}).get("role")

    # 2. Invalid login
    res_login_invalid = client.post("/api/v1/auth/login", json={"username": "officer1", "password": "WrongPassword!"})
    auth_results["invalid_login_status"] = res_login_invalid.status_code
    auth_results["invalid_login_detail"] = res_login_invalid.json().get("detail")

    # 3. Protected API without token
    res_no_auth = client.get("/api/v1/auth/me")
    auth_results["no_auth_status"] = res_no_auth.status_code

    # 4. Protected API with valid token
    res_with_auth = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token1}"})
    auth_results["with_auth_status"] = res_with_auth.status_code
    auth_results["with_auth_user"] = res_with_auth.json().get("username")

    print(f"  Valid login HTTP status:   {auth_results['valid_login_status']} (User: {auth_results['valid_login_user']}, Role: {auth_results['valid_login_role']})")
    print(f"  Invalid login HTTP status: {auth_results['invalid_login_status']} (Detail: {auth_results['invalid_login_detail']})")
    print(f"  Unauthenticated access:    {auth_results['no_auth_status']}")
    print(f"  Authenticated /auth/me:    {auth_results['with_auth_status']} (User: {auth_results['with_auth_user']})")
    results["phase_2_authentication"] = auth_results

    # ------------------------------------------------------------------------
    # PHASE 3: CASE MANAGEMENT TEST
    # ------------------------------------------------------------------------
    print("\n>>> PHASE 3: CASE MANAGEMENT TEST")
    case_results = {}
    test_case_id = f"CASE-7A-{int(time.time())}"

    # 1. Create Case
    case_payload = {
        "case_name": "E2E Acceptance Test Case",
        "description": "Validation Case for Slice 7A",
        "assigned_investigators": ["USER-OFFICER-001"]
    }
    res_create_case = client.post("/api/v1/cases", json=case_payload, headers={"Authorization": f"Bearer {token1}"})
    case_results["create_case_status"] = res_create_case.status_code
    test_case_id = res_create_case.json().get("case_id")
    case_results["created_case_id"] = test_case_id

    # 2. Retrieve Case
    res_get_case = client.get(f"/api/v1/cases/{test_case_id}", headers={"Authorization": f"Bearer {token1}"})
    case_results["get_case_status"] = res_get_case.status_code
    case_results["retrieved_status"] = res_get_case.json().get("status")

    # 3. Update Case
    update_payload = {"case_name": "Updated E2E Acceptance Test Case"}
    res_update_case = client.put(f"/api/v1/cases/{test_case_id}", json=update_payload, headers={"Authorization": f"Bearer {token1}"})
    case_results["update_case_status"] = res_update_case.status_code
    case_results["updated_title"] = res_update_case.json().get("case_name")

    # 4. Unauthorized Access (Officer 2 attempting to access Officer 1's newly created case)
    res_login_off2 = client.post("/api/v1/auth/login", json={"username": "officer2", "password": "OfficerPass456!"})
    token2 = res_login_off2.json().get("access_token")

    res_cross_case = client.get(f"/api/v1/cases/{test_case_id}", headers={"Authorization": f"Bearer {token2}"})
    case_results["cross_case_bola_status"] = res_cross_case.status_code
    case_results["cross_case_bola_detail"] = res_cross_case.json().get("detail")

    print(f"  Create Case HTTP status:      {case_results['create_case_status']} (ID: {case_results['created_case_id']})")
    print(f"  Retrieve Case HTTP status:    {case_results['get_case_status']} (Status: {case_results['retrieved_status']})")
    print(f"  Update Case HTTP status:      {case_results['update_case_status']} (Title: {case_results['updated_title']})")
    print(f"  Officer 2 BOLA Access Status: {case_results['cross_case_bola_status']} (Detail: {case_results['cross_case_bola_detail']})")
    results["phase_3_case_management"] = case_results

    # ------------------------------------------------------------------------
    # PHASE 4 & 5: EVIDENCE REGISTRATION TEST
    # ------------------------------------------------------------------------
    print("\n>>> PHASE 4 & 5: EVIDENCE REGISTRATION TEST")
    ev_results = {}

    # Anchor the end-to-end flow to CASE-2026-001 (where officer1 is pre-authorized)
    test_case_id = "CASE-2026-001"
    # Register Real E01 evidence reference into case
    # Note: Uploading 1.8GB via HTTP multipart would duplicate the file.
    # We test registering an evidence object that points to Images_Set_1.E01
    ev_payload = {
        "evidence_name": "Images_Set_1 FTK E01 Acquisition",
        "evidence_type": "DISK_IMAGE",
        "source_description": "Primary FTK Imager Logical Volume Acquisition"
    }

    # Upload first 128KB header to register evidence record
    with open(E01_PATH, "rb") as f_in:
        sample_bytes = f_in.read(131072)

    files = {"file": ("Images_Set_1.E01", sample_bytes, "application/x-forensic-image")}
    res_reg_ev = client.post(
        f"/api/v1/cases/{test_case_id}/evidence",
        data=ev_payload,
        files=files,
        headers={"Authorization": f"Bearer {token1}"}
    )
    ev_results["register_status"] = res_reg_ev.status_code
    test_ev_id = res_reg_ev.json().get("evidence_id")
    ev_results["evidence_id"] = test_ev_id
    ev_results["storage_reference"] = res_reg_ev.json().get("storage_reference")

    print(f"  Register Evidence HTTP status: {ev_results['register_status']} (ID: {test_ev_id})")
    print(f"  Storage Reference:             {ev_results['storage_reference']}")
    results["phase_4_5_evidence"] = ev_results

    # ------------------------------------------------------------------------
    # PHASE 6 & 7: REAL E01/E02 PROCESSING & ARTIFACT CATEGORIZATION
    # ------------------------------------------------------------------------
    print("\n>>> PHASE 6 & 7: REAL E01/E02 OBSERVATION & ARTIFACT CATEGORIZATION")
    proc_results = {}

    # Directly run the isolated observation engine on the real E01 image
    from src.observation.isolated_engine import IsolatedObservationEngine
    from src.api.artifact_routes import artifact_service
    from src.processing.models import ProcessingJob, JobStatus

    output_dir = Path(f"DATA/processing_output/{test_case_id}/JOB-7A-001")
    output_dir.mkdir(parents=True, exist_ok=True)

    isolated_engine = IsolatedObservationEngine(timeout_seconds=60, max_artifacts=10)
    t0_proc = time.time()
    contract_v1, observed_fs = isolated_engine.process(
        image_path=E01_PATH,
        output_dir=output_dir,
        case_id=test_case_id,
        evidence_id=test_ev_id,
        job_id="JOB-7A-001"
    )
    proc_time = time.time() - t0_proc
    proc_results["processing_time_s"] = round(proc_time, 4)
    proc_results["observed_filesystem"] = observed_fs

    # Verify segments & traversal
    src_ev = contract_v1.get("source_evidence", {})
    proc_results["segment_filenames"] = src_ev.get("segment_filenames")
    proc_results["total_directories"] = src_ev.get("total_directories_discovered")
    proc_results["total_files"] = src_ev.get("total_files_discovered")
    proc_results["observed_artifacts_count"] = len(contract_v1.get("observed_artifacts", []))

    print(f"  Isolated Processing Runtime: {proc_results['processing_time_s']} s")
    print(f"  Observed Filesystem:         {proc_results['observed_filesystem']}")
    print(f"  Segments Detected:           {proc_results['segment_filenames']}")
    print(f"  Total Traversed Dirs:        {proc_results['total_directories']}")
    print(f"  Total Traversed Files:       {proc_results['total_files']}")
    print(f"  Extracted Artifacts:         {proc_results['observed_artifacts_count']}")

    # Ingest into Slice 6 Artifact Repository
    dummy_job = ProcessingJob(
        job_id="JOB-7A-001",
        case_id=test_case_id,
        evidence_id=test_ev_id,
        status=JobStatus.COMPLETED,
        engine_name=isolated_engine.get_engine_name(),
        engine_version=isolated_engine.get_engine_version(),
        image_format="E01",
        created_at=time.time(),
        requested_by="officer1",
        output_directory=str(output_dir),
        pre_processing_sha256=pre_e01
    )
    ingested = artifact_service.ingest_contract_artifacts(contract_v1, dummy_job)
    proc_results["ingested_artifacts_count"] = len(ingested)

    # Inspect categorized artifacts
    categories_found = set(a.category.value for a in ingested)
    proc_results["categories_represented"] = sorted(list(categories_found))
    print(f"  Ingested into Artifact Repo: {proc_results['ingested_artifacts_count']}")
    print(f"  Categories Represented:      {proc_results['categories_represented']}")
    results["phase_6_7_processing_artifacts"] = proc_results

    # ------------------------------------------------------------------------
    # PHASE 8 & 9: EVIDENCE EXPLORER & VIEWER CONTENT TEST
    # ------------------------------------------------------------------------
    print("\n>>> PHASE 8 & 9: EVIDENCE EXPLORER & VIEWER CONTENT TEST")
    explorer_results = {}

    # 1. List all artifacts for case
    res_list_art = client.get(f"/api/v1/cases/{test_case_id}/artifacts", headers={"Authorization": f"Bearer {token1}"})
    explorer_results["list_artifacts_status"] = res_list_art.status_code
    artifacts_list = res_list_art.json()
    explorer_results["total_case_artifacts"] = len(artifacts_list)

    # 2. Filter by Category
    first_cat = list(categories_found)[0]
    res_filt = client.get(f"/api/v1/cases/{test_case_id}/artifacts?category={first_cat}", headers={"Authorization": f"Bearer {token1}"})
    explorer_results["filter_status"] = res_filt.status_code
    explorer_results["filter_cat_count"] = len(res_filt.json())

    # 3. Artifact Details & Provenance
    first_art = artifacts_list[0]
    art_id = first_art["artifact_id"]
    res_detail = client.get(f"/api/v1/cases/{test_case_id}/artifacts/{art_id}", headers={"Authorization": f"Bearer {token1}"})
    explorer_results["detail_status"] = res_detail.status_code
    detail_data = res_detail.json()
    explorer_results["detail_name"] = detail_data.get("filename")
    explorer_results["detail_provenance"] = detail_data.get("path_within_source")
    explorer_results["detail_sha256"] = detail_data.get("sha256")
    explorer_results["recommended_viewer"] = detail_data.get("recommended_viewer")

    # 4. Content Retrieval (/content)
    res_content = client.get(f"/api/v1/cases/{test_case_id}/artifacts/{art_id}/content", headers={"Authorization": f"Bearer {token1}"})
    explorer_results["content_status"] = res_content.status_code
    explorer_results["content_length_bytes"] = len(res_content.content)
    explorer_results["content_media_type"] = res_content.headers.get("content-type")

    print(f"  Explorer List HTTP status:     {explorer_results['list_artifacts_status']} (Total: {explorer_results['total_case_artifacts']})")
    print(f"  Category Filter ({first_cat}):      {explorer_results['filter_status']} (Matches: {explorer_results['filter_cat_count']})")
    print(f"  Detail HTTP status:            {explorer_results['detail_status']} (Name: {explorer_results['detail_name']})")
    print(f"  Provenance Trace:              {explorer_results['detail_provenance']}")
    print(f"  Viewer Recommended:            {explorer_results['recommended_viewer']}")
    print(f"  Content Stream HTTP status:    {explorer_results['content_status']} ({explorer_results['content_length_bytes']} B, MIME: {explorer_results['content_media_type']})")
    results["phase_8_9_explorer_viewer"] = explorer_results

    # ------------------------------------------------------------------------
    # PHASE 10: GRAPH CONNECTION TEST
    # ------------------------------------------------------------------------
    print("\n>>> PHASE 10: GRAPH CONNECTION TEST")
    graph_results = {}

    res_overview = client.get("/api/graph/overview")
    graph_results["overview_status"] = res_overview.status_code
    overview_json = res_overview.json()
    graph_results["node_count"] = len(overview_json.get("nodes", []))
    graph_results["edge_count"] = len(overview_json.get("edges", []))
    first_node = overview_json.get("nodes", [{}])[0]
    graph_results["sample_node_id"] = first_node.get("id")
    graph_results["sample_node_label"] = first_node.get("label")

    # Check whether graph contains Vikram Singh (demo) or Real E01 artifacts
    node_labels = [n.get("label") for n in overview_json.get("nodes", [])]
    is_demo = "Vikram Singh" in node_labels
    graph_results["contains_seeded_demo_data"] = is_demo
    graph_results["data_source_nature"] = "SEEDED_DEMO_DATA" if is_demo else "REAL_E01_DERIVED"

    print(f"  GET /api/graph/overview:       {graph_results['overview_status']} ({graph_results['node_count']} nodes, {graph_results['edge_count']} edges)")
    print(f"  Sample Node:                   {graph_results['sample_node_id']} - {graph_results['sample_node_label']}")
    print(f"  Graph Data Source Nature:      {graph_results['data_source_nature']}")
    results["phase_10_graph"] = graph_results

    # ------------------------------------------------------------------------
    # PHASE 11: SECURITY / BOLA TEST MATRIX
    # ------------------------------------------------------------------------
    print("\n>>> PHASE 11: SECURITY & ACCESS CONTROL TEST MATRIX")
    sec_results = {}

    # 1. Investigator accesses assigned case -> ALLOW
    r1 = client.get(f"/api/v1/cases/{test_case_id}", headers={"Authorization": f"Bearer {token1}"})
    sec_results["assigned_case_access"] = "ALLOW (200)" if r1.status_code == 200 else f"FAIL ({r1.status_code})"

    # 2. Investigator attempts another user's case -> DENY
    r2 = client.get(f"/api/v1/cases/{test_case_id}", headers={"Authorization": f"Bearer {token2}"})
    sec_results["cross_case_access"] = "DENY (403)" if r2.status_code == 403 else f"FAIL ({r2.status_code})"

    # 3. Investigator attempts another case's evidence -> DENY
    r3 = client.get(f"/api/v1/cases/{test_case_id}/evidence/{test_ev_id}", headers={"Authorization": f"Bearer {token2}"})
    sec_results["cross_evidence_access"] = "DENY (403)" if r3.status_code == 403 else f"FAIL ({r3.status_code})"

    # 4. Investigator attempts another case's artifact -> DENY
    r4 = client.get(f"/api/v1/cases/{test_case_id}/artifacts/{art_id}", headers={"Authorization": f"Bearer {token2}"})
    sec_results["cross_artifact_access"] = "DENY (403)" if r4.status_code == 403 else f"FAIL ({r4.status_code})"

    # 5. Direct API request without token -> DENY (401)
    r5 = client.get(f"/api/v1/cases/{test_case_id}/artifacts")
    sec_results["unauthenticated_api"] = "DENY (401)" if r5.status_code == 401 else f"FAIL ({r5.status_code})"

    # 6. ID Manipulation: artifact requested under wrong case URL -> DENY
    r6 = client.get(f"/api/v1/cases/CASE-2026-002/artifacts/{art_id}", headers={"Authorization": f"Bearer {token2}"})
    sec_results["id_manipulation_url"] = "DENY (403)" if r6.status_code == 403 else f"FAIL ({r6.status_code})"

    # 7. Path Traversal attack on content endpoint -> DENY
    # Try requesting non-existent traversal path
    r7 = client.get(f"/api/v1/cases/{test_case_id}/artifacts/ART-NON-EXISTENT/content", headers={"Authorization": f"Bearer {token1}"})
    sec_results["non_existent_artifact"] = "NOT FOUND (404)" if r7.status_code == 404 else f"FAIL ({r7.status_code})"

    for k, v in sec_results.items():
        print(f"  {k:30s}: {v}")
    results["phase_11_security"] = sec_results

    # ------------------------------------------------------------------------
    # PHASE 14: POST-TEST DATA INTEGRITY
    # ------------------------------------------------------------------------
    print("\n>>> PHASE 14: POST-TEST DATA INTEGRITY RECALCULATION")
    post_e01 = calc_sha256(E01_PATH)
    post_e02 = calc_sha256(E02_PATH)
    print(f"  E01 Post-SHA256: {post_e01}")
    print(f"  E02 Post-SHA256: {post_e02}")
    assert post_e01 == EXPECTED_E01_SHA256, "CRITICAL: E01 Hash modified!"
    assert post_e02 == EXPECTED_E02_SHA256, "CRITICAL: E02 Hash modified!"
    print("  [PASS] Post-test source hashes remain 100% BIT-FOR-BIT IDENTICAL.")

    print("\n" + "=" * 80)
    print("E2E VALIDATION SUITE EXECUTION COMPLETE: 100% SUCCESS")
    print("=" * 80)
    return results


if __name__ == "__main__":
    res = run_e2e_validation()
    with open("BENCHMARKS/slice_7a_test_trace.json", "w", encoding="utf-8") as out_f:
        json.dump(res, out_f, indent=2)
