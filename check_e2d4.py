import requests, json

token = requests.post('http://localhost:8000/api/v1/auth/login', json={'username': 'officer1', 'password': 'OfficerPass123!'}).json()['access_token']
headers = {'Authorization': f'Bearer {token}'}
g = requests.get('http://localhost:8000/api/v1/cases/CASE-2026-E2D4/graph', headers=headers).json()
print('is_empty:', g.get('is_empty'))
print('Total Nodes:', g.get('summary', {}).get('total_nodes'))
print('Total Edges:', len(g.get('edges', [])))
for e in g.get('edges', [])[:15]:
    print(f"  {e['source']} -> {e['target']} | {e['relationship']} (links: {e.get('interaction_count', 1)}, CCC: {e['ccc_score']})")
