import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
db = sqlite3.connect('DATA/cases.db')
cols = [r[1] for r in db.execute('PRAGMA table_info(artifacts)').fetchall()]
print('ARTIFACT COLUMNS:', cols)
count = db.execute('SELECT COUNT(*) FROM artifacts WHERE case_id=?', ('CASE-2026-EADC',)).fetchone()[0]
print(f'Total artifacts for CASE-2026-EADC: {count}')
rows = db.execute('SELECT * FROM artifacts WHERE case_id=? LIMIT 30', ('CASE-2026-EADC',)).fetchall()
for r in rows:
    print(r[:6])
db.close()
