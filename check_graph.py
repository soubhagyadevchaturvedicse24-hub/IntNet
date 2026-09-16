import requests, json

token = requests.post('http://localhost:8000/api/v1/auth/login', json={'username': 'officer1', 'password': 'OfficerPass123!'}).json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

r = requests.get('http://localhost:8000/api/v1/cases/CASE-2026-C1EA/graph', headers=headers)
data = r.json()
print('is_empty:', data.get('is_empty'))
print('total_nodes:', data.get('summary', {}).get('total_nodes'))
print('total_edges:', data.get('summary', {}).get('total_edges'))
print('message:', data.get('message', 'NONE'))
nodes = data.get('nodes', [])
edges = data.get('edges', [])
print(f'\nNodes ({len(nodes)}):')
for n in nodes:
    print(f"  [{n['entity_type']}] {n['label']} (layer={n['layer']})")
print(f'\nEdges ({len(edges)}):')
for e in edges[:5]:
    print(f"  {e['source']} --{e['relationship_type']}--> {e['target']}")
