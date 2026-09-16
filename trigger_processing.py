"""
CRIMENET — Force-trigger processing pipeline for CASE-2026-EADC evidence.
Run this script after restarting the server to kick off artifact extraction.
"""
import sqlite3
import hashlib
import requests
import json
import sys
import time

BASE_URL = "http://localhost:8000"
CASE_ID = "CASE-2026-EADC"
EVIDENCE_ID = "EV-2026-4092C99D95A7"

# ── Step 1: Login ─────────────────────────────────────────────────────────────
print("[1] Logging in as officer1...")
resp = requests.post(f"{BASE_URL}/api/v1/auth/login",
    json={"username": "officer1", "password": "OfficerPass123!"})
if resp.status_code != 200:
    print(f"    LOGIN FAILED: {resp.status_code} {resp.text}")
    sys.exit(1)
token = resp.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}
print(f"    OK. Token acquired.")

# ── Step 2: Verify evidence exists ────────────────────────────────────────────
print(f"[2] Checking evidence {EVIDENCE_ID} under {CASE_ID}...")
resp = requests.get(f"{BASE_URL}/api/v1/cases/{CASE_ID}/evidence/{EVIDENCE_ID}", headers=headers)
if resp.status_code == 200:
    ev = resp.json()
    print(f"    FOUND: {ev.get('original_filename')} — SHA256: {ev.get('sha256', 'N/A')[:16]}...")
    print(f"    Storage ref: {ev.get('storage_reference')}")
else:
    print(f"    Evidence not found: {resp.status_code} {resp.text}")
    # Try to list all evidence for the case
    resp2 = requests.get(f"{BASE_URL}/api/v1/cases/{CASE_ID}/evidence", headers=headers)
    print(f"    All evidence for {CASE_ID}: {resp2.text[:500]}")
    sys.exit(1)

# ── Step 3: Check existing jobs ───────────────────────────────────────────────
print(f"[3] Checking existing jobs for evidence...")
resp = requests.get(f"{BASE_URL}/api/v1/cases/{CASE_ID}/evidence/{EVIDENCE_ID}/jobs", headers=headers)
if resp.status_code == 200:
    jobs = resp.json()
    print(f"    Existing jobs: {len(jobs)}")
    for j in jobs:
        print(f"    JOB {j.get('job_id')}: status={j.get('status')}, error={j.get('error_message')}")
    if jobs and all(j.get('status') in ['QUEUED', 'RUNNING'] for j in jobs):
        print("    A job is already running. Monitoring...")
        sys.exit(0)
else:
    print(f"    Could not list jobs: {resp.status_code} {resp.text}")

# ── Step 4: Trigger processing ────────────────────────────────────────────────
print(f"[4] Triggering processing pipeline...")
resp = requests.post(
    f"{BASE_URL}/api/v1/cases/{CASE_ID}/evidence/{EVIDENCE_ID}/process",
    headers=headers,
    json={}
)
if resp.status_code in [200, 201, 202]:
    job = resp.json()
    job_id = job.get("job_id")
    print(f"    Processing job created: {job_id}")
    print(f"    Status: {job.get('status')}")
    print(f"    Engine: {job.get('engine_name')}")
    print()
    print(f"  --> Job is now running in background.")
    print(f"  --> This will take 5-30 minutes for a 1.88 GB E01 image.")
    print(f"  --> Poll status: GET /api/v1/processing/jobs/{job_id}")
    print()
    print(f"  Run this to check progress:")
    print(f"  python -c \"import requests; r=requests.get('http://localhost:8000/api/v1/processing/jobs/{job_id}', headers={{'Authorization': 'Bearer {token}'}}); print(r.json().get('status'), r.json().get('error_message'))\"")
else:
    print(f"    FAILED: {resp.status_code}")
    print(f"    Detail: {resp.text}")
    sys.exit(1)
