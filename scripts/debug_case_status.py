from src.api.main import app
from fastapi.testclient import TestClient
import sqlite3

client = TestClient(app)
res = client.post('/api/v1/auth/login', json={'username': 'officer1', 'password': 'OfficerPass123!'})
token = res.json()['access_token']
c = client.post('/api/v1/cases', headers={'Authorization': f'Bearer {token}'}, json={'case_name': 'T', 'description': 'D'}).json()
cid = c['case_id']
print('Created POST response status:', c['status'])

conn = sqlite3.connect('DATA/cases.db')
cur = conn.cursor()
cur.execute('SELECT case_id, status FROM cases WHERE case_id = ?', (cid,))
print('Direct SQLite status:', cur.fetchone())

g = client.get(f'/api/v1/cases/{cid}', headers={'Authorization': f'Bearer {token}'}).json()
print('GET endpoint response status:', g['status'])

cur.execute('SELECT case_id, status FROM cases WHERE case_id = ?', (cid,))
print('Direct SQLite status after GET:', cur.fetchone())
