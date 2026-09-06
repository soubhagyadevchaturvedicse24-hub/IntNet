"""
Synthetic Forensic Fixture Generator for CRIMENET Phase 1 Benchmark.
Generates a deterministic synthetic forensic data structure (SYN-IMAGE-01) with ground-truth manifest, EXIF photos, SQLite DBs, and computes master SHA-256.
"""

import os
import json
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

FIXTURE_DIR = Path("D:/Proto SIH/DATA/fixtures/SYN_IMAGE_01")
MANIFEST_PATH = Path("D:/Proto SIH/DATA/fixtures/SYN_FORENSIC_GROUND_TRUTH.json")

def create_sqlite_dbs(base_path: Path):
    db_dir = base_path / "data" / "data" / "com.android.providers.contacts" / "databases"
    db_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. contacts2.db
    contacts_path = db_dir / "contacts2.db"
    conn = sqlite3.connect(contacts_path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE contacts (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, email TEXT);")
    contacts_data = [
        (1, "Rajesh Kumar", "+919876543210", "rajesh.k@example.com"),
        (2, "Vikram Singh", "+919123456780", "vikram.s@example.com"),
        (3, "Amit Sharma", "+919988776655", "amit.s@example.com"),
        (4, "Priya Patel", "+919765432109", "priya.p@example.com"),
        (5, "Suresh Verma", "+919543210987", "suresh.v@example.com"),
    ]
    cur.executemany("INSERT INTO contacts VALUES (?, ?, ?, ?);", contacts_data)
    conn.commit()
    conn.close()

    # 2. calllog.db
    call_dir = base_path / "data" / "data" / "com.android.providers.telephony" / "databases"
    call_dir.mkdir(parents=True, exist_ok=True)
    calllog_path = call_dir / "calllog.db"
    conn = sqlite3.connect(calllog_path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE calls (id INTEGER PRIMARY KEY, caller TEXT, recipient TEXT, call_type TEXT, timestamp TEXT, duration_sec INTEGER);")
    call_data = [
        (1, "+919876543210", "+919123456780", "OUTGOING", "2026-08-15T14:25:10Z", 184),
        (2, "+919123456780", "+919876543210", "INCOMING", "2026-08-15T16:10:00Z", 45),
        (3, "+919988776655", "+919876543210", "INCOMING", "2026-08-16T09:30:15Z", 310),
        (4, "+919876543210", "+919765432109", "OUTGOING", "2026-08-16T11:45:22Z", 92),
    ]
    cur.executemany("INSERT INTO calls VALUES (?, ?, ?, ?, ?, ?);", call_data)
    conn.commit()
    conn.close()

def create_synthetic_photos(base_path: Path):
    media_dir = base_path / "data" / "media" / "0" / "DCIM" / "Camera"
    media_dir.mkdir(parents=True, exist_ok=True)
    
    photo_records = []
    # Create synthetic JPEG files
    for i in range(1, 6):
        photo_name = f"IMG_20260814_1420{i:02d}.jpg"
        photo_path = media_dir / photo_name
        # Simple minimal valid JPEG header bytes + dummy payload
        jpeg_header = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xFF\xDB\x00C\x00" + (b"\x00" * 100) + b"\xFF\xD9"
        with open(photo_path, "wb") as f:
            f.write(jpeg_header)
        
        photo_hash = hashlib.sha256(jpeg_header).hexdigest()
        photo_records.append({
            "file_name": photo_name,
            "path": str(photo_path.relative_to(base_path)).replace("\\", "/"),
            "size_bytes": len(jpeg_header),
            "sha256": photo_hash,
            "exif": {
                "make": "SyntheticPhone",
                "model": "Pro-10",
                "datetime_original": f"2026-08-14T14:20:{i:02d}Z",
                "gps_latitude": 28.6139 + (i * 0.001),
                "gps_longitude": 77.2090 + (i * 0.001),
                "altitude_m": 215.0
            }
        })
    return photo_records

def main():
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generating synthetic forensic fixture in {FIXTURE_DIR}...")
    
    create_sqlite_dbs(FIXTURE_DIR)
    photos = create_synthetic_photos(FIXTURE_DIR)
    
    # Compute master directory hash
    sha256 = hashlib.sha256()
    file_manifest = []
    for root, dirs, files in sorted(os.walk(FIXTURE_DIR)):
        for f in sorted(files):
            fp = Path(root) / f
            rel_p = str(fp.relative_to(FIXTURE_DIR)).replace("\\", "/")
            with open(fp, "rb") as file_obj:
                data = file_obj.read()
                file_hash = hashlib.sha256(data).hexdigest()
                sha256.update(file_hash.encode("utf-8"))
                file_manifest.append({
                    "relative_path": rel_p,
                    "size_bytes": len(data),
                    "sha256": file_hash
                })
                
    master_hash = sha256.hexdigest()
    
    ground_truth = {
        "fixture_id": "SYN-IMAGE-01",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "master_sha256": master_hash,
        "files_count": len(file_manifest),
        "files": file_manifest,
        "photos_exif": photos,
        "contacts_count": 5,
        "call_records_count": 4
    }
    
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)
        
    print(f"Fixture generation complete.")
    print(f"Master SHA-256: {master_hash}")
    print(f"Ground-Truth Manifest saved to: {MANIFEST_PATH}")

if __name__ == "__main__":
    main()
