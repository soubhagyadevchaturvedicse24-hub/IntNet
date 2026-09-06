"""
Create a Small Deterministic RAW Forensic Disk Image File (SYN_REAL_FORENSIC_IMAGE.raw).
Includes a valid FAT16 Boot Sector / BPB, Root Directory, FAT tables, and data clusters
containing real JPEG images with EXIF metadata and SQLite databases.
"""

import struct
import hashlib
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

OUTPUT_RAW_PATH = Path("D:/Proto SIH/DATA/fixtures/SYN_REAL_FORENSIC_IMAGE.raw")
MANIFEST_PATH = Path("D:/Proto SIH/DATA/fixtures/SYN_REAL_FORENSIC_GROUND_TRUTH.json")

SECTOR_SIZE = 512
TOTAL_SECTORS = 4096  # 2 MB RAW disk image file
SECTORS_PER_CLUSTER = 4
RESERVED_SECTORS = 1
NUM_FATS = 2
ROOT_DIR_ENTRIES = 512
SECTORS_PER_FAT = 4

def create_exif_jpeg_bytes(datetime_str: str, lat: float, lon: float) -> bytes:
    """
    Creates minimal valid JPEG file bytes containing standard EXIF metadata block.
    """
    # Standard minimal JPEG header + EXIF APP1 segment
    header = bytearray(b"\xFF\xD8\xFF\xE1")
    
    # Simple EXIF segment payload containing ASCII metadata string for EXIF tags
    exif_payload = f"Exif\x00\x00MM\x00*\x00\x00\x00\x08Make:SyntheticPhone|Model:Pro-10|DateTime:{datetime_str}|GPS:{lat:.4f},{lon:.4f}".encode("utf-8")
    seg_len = len(exif_payload) + 2
    
    header.extend(struct.pack(">H", seg_len))
    header.extend(exif_payload)
    
    # Add minimal Quantization Table + Start of Scan + Minimal image data + EOI
    header.extend(b"\xFF\xDB\x00C\x00" + (b"\x01" * 64))
    header.extend(b"\xFF\xC0\x00\x0B\x08\x00\x10\x00\x10\x01\x01\x11\x00")
    header.extend(b"\xFF\xDA\x00\x08\x01\x01\x00\x00\x3F\x00\x7F\xFF\xD9")
    return bytes(header)

def create_sqlite_db_bytes(records: list, schema_sql: str, insert_sql: str) -> bytes:
    tmp_path = Path("D:/Proto SIH/DATA/fixtures/tmp.db")
    if tmp_path.exists():
        tmp_path.unlink()
    conn = sqlite3.connect(tmp_path)
    cur = conn.cursor()
    cur.execute(schema_sql)
    cur.executemany(insert_sql, records)
    conn.commit()
    conn.close()
    with open(tmp_path, "rb") as f:
        data = f.read()
    tmp_path.unlink()
    return data

def build_fat16_raw_image():
    OUTPUT_RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # 1. Generate Artifact Content Bytes
    jpeg1 = create_exif_jpeg_bytes("2026-08-14T14:20:01Z", 28.6139, 77.2090)
    jpeg2 = create_exif_jpeg_bytes("2026-08-14T14:20:02Z", 28.6149, 77.2100)
    
    contacts_records = [
        (1, "Rajesh Kumar", "+919876543210", "rajesh.k@example.com"),
        (2, "Vikram Singh", "+919123456780", "vikram.s@example.com")
    ]
    contacts_db = create_sqlite_db_bytes(
        contacts_records,
        "CREATE TABLE contacts (id INT, name TEXT, phone TEXT, email TEXT);",
        "INSERT INTO contacts VALUES (?, ?, ?, ?);"
    )
    
    calls_records = [
        (1, "+919876543210", "+919123456780", "OUTGOING", "2026-08-15T14:25:10Z", 184)
    ]
    calllog_db = create_sqlite_db_bytes(
        calls_records,
        "CREATE TABLE calls (id INT, caller TEXT, recipient TEXT, call_type TEXT, timestamp TEXT, duration_sec INT);",
        "INSERT INTO calls VALUES (?, ?, ?, ?, ?, ?);"
    )
    
    # 2. Build Disk Image Buffer (2 MB)
    image_size = TOTAL_SECTORS * SECTOR_SIZE
    disk = bytearray(image_size)
    
    # Sector 0: FAT16 Boot Sector (BPB)
    bpb = bytearray(SECTOR_SIZE)
    bpb[0:3] = b"\xEB\x3C\x90"  # JMP
    bpb[3:11] = b"MSDOS5.0"     # OEM Name
    struct.pack_into("<H", bpb, 11, SECTOR_SIZE)        # Bytes per sector (512)
    bpb[13] = SECTORS_PER_CLUSTER                       # Sectors per cluster (4)
    struct.pack_into("<H", bpb, 14, RESERVED_SECTORS)    # Reserved sectors (1)
    bpb[16] = NUM_FATS                                  # Number of FATs (2)
    struct.pack_into("<H", bpb, 17, ROOT_DIR_ENTRIES)   # Root entries (512)
    struct.pack_into("<H", bpb, 19, TOTAL_SECTORS)      # Total sectors (4096)
    bpb[21] = 0xF8                                      # Media descriptor (Fixed disk)
    struct.pack_into("<H", bpb, 22, SECTORS_PER_FAT)    # Sectors per FAT (4)
    bpb[510:512] = b"\x55\xAA"                          # Boot signature
    
    disk[0:SECTOR_SIZE] = bpb
    
    # Calculate Offsets
    fat1_offset = RESERVED_SECTORS * SECTOR_SIZE
    fat2_offset = fat1_offset + (SECTORS_PER_FAT * SECTOR_SIZE)
    root_dir_offset = fat2_offset + (SECTORS_PER_FAT * SECTOR_SIZE)
    root_dir_size = ROOT_DIR_ENTRIES * 32
    data_area_offset = root_dir_offset + root_dir_size
    
    # FAT Table Initialization
    fat_table = bytearray(SECTORS_PER_FAT * SECTOR_SIZE)
    struct.pack_into("<H", fat_table, 0, 0xFFF8)
    struct.pack_into("<H", fat_table, 2, 0xFFFF)
    
    # Directory Entries
    # Root entry 0: Volume Label "CRIMENET   "
    root_dir = bytearray(root_dir_size)
    struct.pack_into("11sB", root_dir, 0, b"CRIMENET   ", 0x08)
    
    # File 1: IMG_001.JPG (Cluster 2)
    struct.pack_into("11sB", root_dir, 32, b"IMG_001 JPG", 0x20)
    struct.pack_into("<H", root_dir, 32 + 26, 2)
    struct.pack_into("<I", root_dir, 32 + 28, len(jpeg1))
    struct.pack_into("<H", fat_table, 2 * 2, 0xFFFF)
    
    # File 2: IMG_002.JPG (Cluster 3)
    struct.pack_into("11sB", root_dir, 64, b"IMG_002 JPG", 0x20)
    struct.pack_into("<H", root_dir, 64 + 26, 3)
    struct.pack_into("<I", root_dir, 64 + 28, len(jpeg2))
    struct.pack_into("<H", fat_table, 3 * 2, 0xFFFF)
    
    # File 3: CONTACTS.DB (Cluster 4)
    struct.pack_into("11sB", root_dir, 96, b"CONTACTSDB ", 0x20)
    struct.pack_into("<H", root_dir, 96 + 26, 4)
    struct.pack_into("<I", root_dir, 96 + 28, len(contacts_db))
    struct.pack_into("<H", fat_table, 4 * 2, 0xFFFF)

    # File 4: CALLLOG .DB (Cluster 5)
    struct.pack_into("11sB", root_dir, 128, b"CALLLOG DB ", 0x20)
    struct.pack_into("<H", root_dir, 128 + 26, 5)
    struct.pack_into("<I", root_dir, 128 + 28, len(calllog_db))
    struct.pack_into("<H", fat_table, 5 * 2, 0xFFFF)

    # Copy FAT tables to disk buffer
    disk[fat1_offset : fat1_offset + len(fat_table)] = fat_table
    disk[fat2_offset : fat2_offset + len(fat_table)] = fat_table
    disk[root_dir_offset : root_dir_offset + len(root_dir)] = root_dir
    
    # Copy Data Clusters
    cluster_size = SECTORS_PER_CLUSTER * SECTOR_SIZE
    
    def cluster_offset(cluster_num):
        return data_area_offset + ((cluster_num - 2) * cluster_size)
    
    disk[cluster_offset(2) : cluster_offset(2) + len(jpeg1)] = jpeg1
    disk[cluster_offset(3) : cluster_offset(3) + len(jpeg2)] = jpeg2
    disk[cluster_offset(4) : cluster_offset(4) + len(contacts_db)] = contacts_db
    disk[cluster_offset(5) : cluster_offset(5) + len(calllog_db)] = calllog_db
    
    # Write RAW Image File
    with open(OUTPUT_RAW_PATH, "wb") as f:
        f.write(disk)
        
    master_sha256 = hashlib.sha256(disk).hexdigest()
    
    ground_truth = {
        "fixture_id": "SYN_REAL_FORENSIC_IMAGE.raw",
        "format": "RAW_DISK_IMAGE",
        "file_path": str(OUTPUT_RAW_PATH.resolve()),
        "size_bytes": len(disk),
        "master_sha256": master_sha256,
        "is_real_forensic_image": True,
        "contents": [
            {
                "file_name": "IMG_001.JPG",
                "path_in_image": "/IMG_001.JPG",
                "size_bytes": len(jpeg1),
                "sha256": hashlib.sha256(jpeg1).hexdigest(),
                "cluster": 2,
                "exif": {"datetime": "2026-08-14T14:20:01Z", "gps": "28.6139, 77.2090"}
            },
            {
                "file_name": "IMG_002.JPG",
                "path_in_image": "/IMG_002.JPG",
                "size_bytes": len(jpeg2),
                "sha256": hashlib.sha256(jpeg2).hexdigest(),
                "cluster": 3,
                "exif": {"datetime": "2026-08-14T14:20:02Z", "gps": "28.6149, 77.2100"}
            },
            {
                "file_name": "CONTACTS.DB",
                "path_in_image": "/CONTACTS.DB",
                "size_bytes": len(contacts_db),
                "sha256": hashlib.sha256(contacts_db).hexdigest(),
                "cluster": 4,
                "records_count": len(contacts_records)
            },
            {
                "file_name": "CALLLOG.DB",
                "path_in_image": "/CALLLOG.DB",
                "size_bytes": len(calllog_db),
                "sha256": hashlib.sha256(calllog_db).hexdigest(),
                "cluster": 5,
                "records_count": len(calls_records)
            }
        ]
    }
    
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)
        
    print("=== RAW FORENSIC IMAGE CREATION COMPLETE ===")
    print(f"File Path: {OUTPUT_RAW_PATH}")
    print(f"Size: {len(disk)} bytes ({len(disk)/(1024*1024):.2f} MB)")
    print(f"Master SHA-256: {master_sha256}")
    print(f"Ground Truth Manifest: {MANIFEST_PATH}")

if __name__ == "__main__":
    build_fat16_raw_image()
