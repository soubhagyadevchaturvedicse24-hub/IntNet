import requests, json

token = requests.post('http://localhost:8000/api/v1/auth/login', json={'username': 'officer1', 'password': 'OfficerPass123!'}).json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

for cid in ['CASE-2026-C1EA', 'CASE-2026-9F29']:
    r = requests.get(f'http://localhost:8000/api/v1/cases/{cid}/graph', headers=headers)
    if r.ok:
        data = r.json()
        print(f'=== {cid} ===')
        print('Total Nodes:', data.get('summary', {}).get('total_nodes'))
        print('Consolidated Edges:', len(data.get('edges', [])))
        for e in data.get('edges', [])[:8]:
            print(f"  {e['source']} -> {e['target']} | {e['relationship']} (links: {e.get('interaction_count')}, CCC: {e['ccc_score']})")
