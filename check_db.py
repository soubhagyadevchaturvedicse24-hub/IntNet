import sqlite3, os

dbs = [
    "DATA/crimenet.db",
    "DATA/cases.db",
]

for db_path in dbs:
    if not os.path.exists(db_path):
        print(f"NOT FOUND: {db_path}")
        continue
    db = sqlite3.connect(db_path)
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print(f"\n=== {db_path} tables: {tables}")
    
    if "processing_jobs" in tables:
        rows = db.execute("SELECT job_id, case_id, status, error_message FROM processing_jobs ORDER BY rowid DESC LIMIT 5").fetchall()
        print("  JOBS:", rows)
    
    if "artifacts" in tables:
        rows = db.execute("SELECT case_id, COUNT(*) FROM artifacts GROUP BY case_id").fetchall()
        print("  ARTIFACTS by case:", rows)
    
    if "evidence" in tables:
        rows = db.execute("SELECT evidence_id, case_id, original_filename, storage_reference FROM evidence ORDER BY rowid DESC LIMIT 5").fetchall()
        print("  EVIDENCE:", rows)
    
    if "cases" in tables:
        rows = db.execute("SELECT case_id, title, status FROM cases ORDER BY rowid DESC LIMIT 5").fetchall()
        print("  CASES:", rows)
    
    db.close()
