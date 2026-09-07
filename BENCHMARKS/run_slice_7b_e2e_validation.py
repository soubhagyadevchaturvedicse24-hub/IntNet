"""
CRIMENET Slice 7B — Investigator Workspace End-to-End Acceptance Validation Test Runner.
Executes the full functional workflow:
Login -> Case List/Select -> Local Evidence Registration -> Integrity Verification ->
Out-of-Process Processing -> Polling Dynamic Observation -> Evidence Explorer ->
Category Filtering -> Artifact Metadata -> Content Streaming (Bearer Auth) ->
BOLA/Security Enforcement -> Cytoscape Graph Demarcation -> Post-Test Forensic Hash Verification.
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
from src.cases.service import CaseService

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


def run_slice_7b_validation():
    print("=" * 85)
    print("CRIMENET SLICE 7B: INVESTIGATOR WORKSPACE FRONTEND <-> BACKEND ACCEPTANCE VALIDATION")
    print("=" * 85)

    results = {}

    # ------------------------------------------------------------------------
    # PRE-TEST FORENSIC INTEGRITY
    # ------------------------------------------------------------------------
    print("\n>>> STEP 0: PRE-TEST SOURCE IMAGE INTEGRITY")
    pre_e01 = calc_sha256(E01_PATH)
    pre_e02 = calc_sha256(E02_PATH)
    print(f"  E01 Pre-SHA256: {pre_e01}")
    print(f"  E02 Pre-SHA256: {pre_e02}")
    assert pre_e01 == EXPECTED_E01_SHA256, "CRITICAL: E01 Pre-test hash mismatch!"
    assert pre_e02 == EXPECTED_E02_SHA256, "CRITICAL: E02 Pre-test hash mismatch!"
    print("  [PASS] Pre-test source hashes match bit-for-bit ground truth.")
    results["pre_test_e01_hash"] = pre_e01
    results["pre_test_e02_hash"] = pre_e02

    # ------------------------------------------------------------------------
    # STEP 1: FRONTEND HTML ENDPOINT (GET /)
    # ------------------------------------------------------------------------
    print("\n>>> STEP 1: FRONTEND WORKSPACE HTML (GET /)")
    res_ui = client.get("/")
    assert res_ui.status_code == 200, f"Failed to load UI: {res_ui.status_code}"
    html = res_ui.text
    assert "<title>CRIMENET // Investigator Workspace</title>" in html
    assert 'id="tab-btn-cases"' in html
    assert 'id="tab-btn-explorer"' in html
    assert 'id="tab-btn-network"' in html
    assert 'id="login-overlay"' in html
    assert 'DEMO / SEEDED GRAPH DATA' in html
    print(f"  [PASS] Single-page UI delivered ({len(html)} bytes). All key tabs, login modal, and demo disclaimer verified.")
    results["step_1_ui_status"] = 200

    # ------------------------------------------------------------------------
    # STEP 2: AUTHENTICATION (POST /api/v1/auth/login, GET /api/v1/auth/me)
    # ------------------------------------------------------------------------
    print("\n>>> STEP 2: AUTHENTICATION & IDENTITY")
    # 1. Valid login officer1
    res_login_off1 = client.post("/api/v1/auth/login", json={"username": "officer1", "password": "OfficerPass123!"})
    assert res_login_off1.status_code == 200, f"Login failed: {res_login_off1.text}"
    token_off1 = res_login_off1.json()["access_token"]
    user_off1 = res_login_off1.json()["user"]
    print(f"  [PASS] Valid Login: user={user_off1['username']}, role={user_off1['role']}")

    # 2. Invalid login
    res_bad = client.post("/api/v1/auth/login", json={"username": "officer1", "password": "WrongPassword"})
    assert res_bad.status_code == 401
    print("  [PASS] Invalid login rejected (401 Unauthorized)")

    # 3. Unauthenticated /me
    res_no_auth = client.get("/api/v1/auth/me")
    assert res_no_auth.status_code == 401
    print("  [PASS] Unauthenticated /me rejected (401 Unauthorized)")

    # 4. Authenticated /me
    res_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_off1}"})
    assert res_me.status_code == 200
    assert res_me.json()["username"] == "officer1"
    print(f"  [PASS] Authenticated /me verified (user={res_me.json()['username']})")

    # 5. Login officer2 (for BOLA cross-case security checks)
    res_login_off2 = client.post("/api/v1/auth/login", json={"username": "officer2", "password": "OfficerPass456!"})
    token_off2 = res_login_off2.json()["access_token"]

    results["step_2_auth"] = {
        "officer1_role": user_off1["role"],
        "officer1_auth_status": 200,
        "bad_login_status": 401
    }

    # ------------------------------------------------------------------------
    # STEP 3: CASE LISTING & DETAILS (GET /api/v1/cases, GET /api/v1/cases/{id})
    # ------------------------------------------------------------------------
    print("\n>>> STEP 3: CASE RETRIEVAL & LISTING")
    # List cases for officer1
    res_cases = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {token_off1}"})
    assert res_cases.status_code == 200
    case_list = res_cases.json()
    assert any(c["case_id"] == "CASE-2026-001" for c in case_list)
    print(f"  [PASS] GET /api/v1/cases returned {len(case_list)} case(s) for officer1.")

    # Get case details
    res_c_det = client.get("/api/v1/cases/CASE-2026-001", headers={"Authorization": f"Bearer {token_off1}"})
    assert res_c_det.status_code == 200
    assert res_c_det.json()["case_id"] == "CASE-2026-001"
    case_title = res_c_det.json().get("case_name") or res_c_det.json().get("title")
    print(f"  [PASS] GET /api/v1/cases/CASE-2026-001: '{case_title}'")

    results["step_3_cases"] = {
        "cases_count": len(case_list),
        "target_case_id": "CASE-2026-001"
    }

    # ------------------------------------------------------------------------
    # STEP 4: EVIDENCE REGISTRATION VIA LOCAL_IMAGE_PATH & SECURITY
    # ------------------------------------------------------------------------
    print("\n>>> STEP 4: EVIDENCE REGISTRATION & LOCAL PATH SECURITY")
    # 1. Path traversal attack attempt
    res_trav = client.post(
        "/api/v1/cases/CASE-2026-001/evidence",
        data={
            "evidence_name": "Malicious Traversal",
            "evidence_type": "DISK_IMAGE",
            "local_image_path": "../../Windows/System32/cmd.exe"
        },
        headers={"Authorization": f"Bearer {token_off1}"}
    )
    assert res_trav.status_code in [400, 403], f"Path traversal should be rejected: {res_trav.status_code}"
    print(f"  [PASS] Path traversal rejected: HTTP {res_trav.status_code} ({res_trav.json().get('detail')})")

    # 2. Non-existent file attempt
    res_nonexist = client.post(
        "/api/v1/cases/CASE-2026-001/evidence",
        data={
            "evidence_name": "Non-existent file",
            "evidence_type": "DISK_IMAGE",
            "local_image_path": "D:/Proto SIH/Images/DoesNotExist_12345.E01"
        },
        headers={"Authorization": f"Bearer {token_off1}"}
    )
    assert res_nonexist.status_code == 400
    print(f"  [PASS] Non-existent local file rejected: HTTP 400 ({res_nonexist.json().get('detail')})")

    # 3. Valid local evidence registration (zero-byte hardlink)
    reg_payload = {
        "evidence_name": "Images_Set_1 FTK Real Acquisition (Slice 7B)",
        "evidence_type": "DISK_IMAGE",
        "source_description": "Validated FTK E01/E02 Disk Acquisition",
        "local_image_path": str(E01_PATH)
    }
    res_reg = client.post(
        "/api/v1/cases/CASE-2026-001/evidence",
        data=reg_payload,
        headers={"Authorization": f"Bearer {token_off1}"}
    )
    assert res_reg.status_code == 201, f"Evidence registration failed: {res_reg.text}"
    ev_data = res_reg.json()
    evidence_id = ev_data["evidence_id"]
    storage_ref = ev_data["storage_reference"]
    print(f"  [PASS] Evidence registered: ID={evidence_id}, ref={storage_ref}")
    print(f"         Hashes: MD5={ev_data.get('md5')}, SHA256={ev_data['sha256'][:16]}...")

    # Confirm companion segment was linked
    stored_e01 = Path("DATA/evidence_store") / storage_ref
    companion_path = Path(str(stored_e01).replace(".E01", ".E02"))
    assert companion_path.exists(), f"Companion E02 segment missing at {companion_path}"
    print(f"  [PASS] Companion E02 segment successfully co-located: {companion_path.name}")

    results["step_4_evidence"] = {
        "evidence_id": evidence_id,
        "storage_reference": storage_ref,
        "sha256": ev_data["sha256"]
    }

    # ------------------------------------------------------------------------
    # STEP 5: EVIDENCE INTEGRITY VERIFICATION
    # ------------------------------------------------------------------------
    print("\n>>> STEP 5: EVIDENCE INTEGRITY VERIFICATION")
    res_verify = client.post(
        f"/api/v1/cases/CASE-2026-001/evidence/{evidence_id}/verify",
        headers={"Authorization": f"Bearer {token_off1}"}
    )
    assert res_verify.status_code == 200, f"Integrity check failed: {res_verify.text}"
    v_data = res_verify.json()
    assert v_data["integrity_status"] == "INTACT"
    assert v_data["calculated_sha256"] == EXPECTED_E01_SHA256
    print(f"  [PASS] Integrity Status: {v_data['integrity_status']}, SHA-256 match confirmed.")
    results["step_5_integrity"] = v_data

    # ------------------------------------------------------------------------
    # STEP 6: OUT-OF-PROCESS OBSERVATION & POLLING DYNAMIC RESULTS
    # ------------------------------------------------------------------------
    print("\n>>> STEP 6: OUT-OF-PROCESS EVIDENCE PROCESSING & OBSERVATION")
    res_proc = client.post(
        f"/api/v1/cases/CASE-2026-001/evidence/{evidence_id}/process",
        headers={"Authorization": f"Bearer {token_off1}"}
    )
    assert res_proc.status_code == 202, f"Processing trigger failed: {res_proc.text}"
    job_id = res_proc.json()["job_id"]
    print(f"  [PASS] Processing dispatched. Job ID: {job_id}")

    # Poll job status
    print("  Polling job status until completion...")
    t_start = time.time()
    job_data = None
    while time.time() - t_start < 60:
        res_job = client.get(
            f"/api/v1/processing/jobs/{job_id}",
            headers={"Authorization": f"Bearer {token_off1}"}
        )
        assert res_job.status_code == 200
        job_data = res_job.json()
        status_val = job_data.get("status")
        if status_val in ["COMPLETED", "FAILED"]:
            break
        time.sleep(0.8)

    assert job_data["status"] == "COMPLETED", f"Job failed or timed out: {job_data}"
    elapsed = round(time.time() - t_start, 2)

    # Fetch Evidence Contract to inspect dynamic discovered counts
    res_contract = client.get(
        f"/api/v1/processing/jobs/{job_id}/contract",
        headers={"Authorization": f"Bearer {token_off1}"}
    )
    assert res_contract.status_code == 200, f"Failed to retrieve contract: {res_contract.text}"
    contract = res_contract.json()
    src_ev = contract.get("source_evidence", {})
    obs_fs = job_data.get("observed_filesystem")
    total_dirs = src_ev.get("total_directories_discovered")
    total_files = src_ev.get("total_files_discovered")
    contract_arts_count = len(contract.get("observed_artifacts", []))

    print(f"  [PASS] Job COMPLETED in {elapsed}s.")
    print(f"         Observed Filesystem:     {obs_fs}")
    print(f"         Directories Traversed:   {total_dirs}")
    print(f"         Files Traversed:         {total_files}")
    print(f"         Contract Artifacts:      {contract_arts_count}")

    # Assert dynamic extraction values (NOT hardcoded, actually parsed from real E01)
    assert obs_fs == "NTFS", f"Expected NTFS, got {obs_fs}"
    assert total_dirs == 1122, f"Expected 1122 directories, got {total_dirs}"
    assert total_files == 2898, f"Expected 2898 files, got {total_files}"
    assert contract_arts_count == 23, f"Expected 23 contract artifacts, got {contract_arts_count}"

    results["step_6_observation"] = {
        "job_id": job_id,
        "elapsed_seconds": elapsed,
        "observed_filesystem": obs_fs,
        "total_directories": total_dirs,
        "total_files": total_files,
        "contract_artifacts_count": contract_arts_count
    }

    # ------------------------------------------------------------------------
    # STEP 7: EVIDENCE EXPLORER & CATEGORIZATION
    # ------------------------------------------------------------------------
    print("\n>>> STEP 7: EVIDENCE EXPLORER & ARTIFACT CATEGORIZATION")
    res_arts = client.get(
        f"/api/v1/cases/CASE-2026-001/artifacts",
        headers={"Authorization": f"Bearer {token_off1}"}
    )
    assert res_arts.status_code == 200
    all_artifacts = res_arts.json()
    print(f"  [PASS] Total artifacts for CASE-2026-001: {len(all_artifacts)}")

    # Category breakdown
    category_counts = {}
    for a in all_artifacts:
        cat = a.get("category", "UNKNOWN")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    print("  Category Distribution:")
    for cat, cnt in sorted(category_counts.items()):
        print(f"    - {cat}: {cnt}")

    # Test category filtering endpoint
    for cat in ["DOCUMENT", "IMAGE", "SPREADSHEET", "DATABASE", "LOG", "OTHER"]:
        if cat in category_counts:
            res_cat = client.get(
                f"/api/v1/cases/CASE-2026-001/artifacts?category={cat}",
                headers={"Authorization": f"Bearer {token_off1}"}
            )
            assert res_cat.status_code == 200
            filtered = res_cat.json()
            assert len(filtered) == category_counts[cat], f"Filter for {cat} returned {len(filtered)} vs expected {category_counts[cat]}"
            print(f"  [PASS] Category Filter '{cat}' verified: {len(filtered)} items.")

    results["step_7_artifacts"] = {
        "total_case_artifacts": len(all_artifacts),
        "categories": category_counts
    }

    # ------------------------------------------------------------------------
    # STEP 8: ARTIFACT DETAILS & PROVENANCE INSPECTION
    # ------------------------------------------------------------------------
    print("\n>>> STEP 8: ARTIFACT DETAILS & PROVENANCE INSPECTION")
    # Find a document artifact to inspect
    doc_artifacts = [a for a in all_artifacts if a.get("category") == "DOCUMENT"]
    target_art = doc_artifacts[0] if doc_artifacts else all_artifacts[0]
    art_id = target_art["artifact_id"]

    res_det = client.get(
        f"/api/v1/cases/CASE-2026-001/artifacts/{art_id}",
        headers={"Authorization": f"Bearer {token_off1}"}
    )
    assert res_det.status_code == 200
    detail = res_det.json()
    print(f"  [PASS] Retrieved Artifact Detail for: {detail.get('filename')}")
    print(f"         Artifact ID:    {detail.get('artifact_id')}")
    print(f"         Category:       {detail.get('category')}")
    print(f"         Size:           {detail.get('size_bytes')} bytes")
    print(f"         SHA-256:        {detail.get('sha256')}")
    print(f"         Extracted Path: {detail.get('path_within_source')}")
    print(f"         Source Ev ID:   {detail.get('evidence_id')}")

    results["step_8_artifact_detail"] = {
        "artifact_id": art_id,
        "filename": detail.get("filename"),
        "category": detail.get("category"),
        "size": detail.get("size_bytes"),
        "sha256": detail.get("sha256")
    }

    # ------------------------------------------------------------------------
    # STEP 9: ARTIFACT CONTENT STREAMING & SECURITY
    # ------------------------------------------------------------------------
    print("\n>>> STEP 9: ARTIFACT CONTENT STREAMING (BEARER AUTH)")
    # 1. Stream content without auth -> 401
    res_stream_noauth = client.get(f"/api/v1/cases/CASE-2026-001/artifacts/{art_id}/content")
    assert res_stream_noauth.status_code == 401
    print("  [PASS] Content streaming without token rejected (401 Unauthorized)")

    # 2. Stream content with valid token
    res_stream = client.get(
        f"/api/v1/cases/CASE-2026-001/artifacts/{art_id}/content",
        headers={"Authorization": f"Bearer {token_off1}"}
    )
    assert res_stream.status_code == 200
    content_len = len(res_stream.content)
    content_type = res_stream.headers.get("content-type")
    print(f"  [PASS] Streamed {content_len} bytes successfully. Content-Type: {content_type}")

    # If it's a PDF, verify binary magic
    if detail.get("filename", "").endswith(".pdf"):
        assert res_stream.content[:5] == b"%PDF-", "PDF magic bytes missing!"
        print("  [PASS] Genuine PDF binary stream verified with %PDF- header.")

    results["step_9_content"] = {
        "stream_status": res_stream.status_code,
        "bytes_streamed": content_len,
        "content_type": content_type
    }

    # ------------------------------------------------------------------------
    # STEP 10: BOLA / BFLA ACCESS CONTROL & SECURITY ENFORCEMENT
    # ------------------------------------------------------------------------
    print("\n>>> STEP 10: BOLA / BFLA AUTHORIZATION DEFENSE MATRIX")
    # Officer 2 attempts to access Officer 1's case data:
    # 1. Access case
    r1 = client.get("/api/v1/cases/CASE-2026-001", headers={"Authorization": f"Bearer {token_off2}"})
    assert r1.status_code == 403, f"Officer 2 should be forbidden from CASE-2026-001: {r1.status_code}"
    print("  [PASS] BOLA Defense: Officer 2 denied access to CASE-2026-001 (403 Forbidden)")

    # 2. Access evidence
    r2 = client.get(f"/api/v1/cases/CASE-2026-001/evidence/{evidence_id}", headers={"Authorization": f"Bearer {token_off2}"})
    assert r2.status_code == 403
    print("  [PASS] BOLA Defense: Officer 2 denied access to case evidence (403 Forbidden)")

    # 3. Access artifacts list
    r3 = client.get("/api/v1/cases/CASE-2026-001/artifacts", headers={"Authorization": f"Bearer {token_off2}"})
    assert r3.status_code == 403
    print("  [PASS] BOLA Defense: Officer 2 denied access to case artifacts list (403 Forbidden)")

    # 4. Access artifact content
    r4 = client.get(f"/api/v1/cases/CASE-2026-001/artifacts/{art_id}/content", headers={"Authorization": f"Bearer {token_off2}"})
    assert r4.status_code == 403
    print("  [PASS] BOLA Defense: Officer 2 denied access to stream artifact content (403 Forbidden)")

    # 5. Non-existent artifact ID
    r5 = client.get("/api/v1/cases/CASE-2026-001/artifacts/NON-EXISTENT-9999", headers={"Authorization": f"Bearer {token_off1}"})
    assert r5.status_code == 404
    print("  [PASS] Non-existent artifact ID returns 404 Not Found")

    results["step_10_security"] = {
        "cross_case_bola_status": 403,
        "unauthorized_content_stream_status": 403,
        "not_found_status": 404
    }

    # ------------------------------------------------------------------------
    # STEP 11: GRAPH INTELLIGENCE DEMARCATION
    # ------------------------------------------------------------------------
    print("\n>>> STEP 11: GRAPH INTELLIGENCE & DEMO DEMARCATION")
    res_graph = client.get("/api/graph/overview")
    assert res_graph.status_code == 200
    g_data = res_graph.json()
    print(f"  [PASS] Graph overview returned {len(g_data.get('nodes', []))} nodes, {len(g_data.get('edges', []))} edges.")
    print("         Graph UI disclaimer explicitly informs investigator that Cytoscape data is Demo/Seeded.")
    results["step_11_graph"] = {
        "nodes_count": len(g_data.get("nodes", [])),
        "edges_count": len(g_data.get("edges", []))
    }

    # ------------------------------------------------------------------------
    # STEP 12: POST-TEST FORENSIC INTEGRITY
    # ------------------------------------------------------------------------
    print("\n>>> STEP 12: POST-TEST FORENSIC INTEGRITY VERIFICATION")
    post_e01 = calc_sha256(E01_PATH)
    post_e02 = calc_sha256(E02_PATH)
    print(f"  E01 Post-SHA256: {post_e01}")
    print(f"  E02 Post-SHA256: {post_e02}")
    assert post_e01 == EXPECTED_E01_SHA256, "CRITICAL: E01 post-test hash changed!"
    assert post_e02 == EXPECTED_E02_SHA256, "CRITICAL: E02 post-test hash changed!"
    assert post_e01 == pre_e01, "E01 modified during execution!"
    assert post_e02 == pre_e02, "E02 modified during execution!"
    print("  [PASS] Bit-for-bit source image integrity preserved. ZERO modifications.")
    results["post_test_e01_hash"] = post_e01
    results["post_test_e02_hash"] = post_e02

    # Save summary JSON for reports
    out_json_path = Path("BENCHMARKS/slice_7b_e2e_results.json")
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[COMPLETE] Validation results saved to {out_json_path}")
    return results


if __name__ == "__main__":
    run_slice_7b_validation()
