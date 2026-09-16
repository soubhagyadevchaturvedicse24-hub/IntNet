import requests, time, json

token = requests.post('http://localhost:8000/api/v1/auth/login', json={'username': 'officer1', 'password': 'OfficerPass123!'}).json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

# 1. Create Case
c_resp = requests.post('http://localhost:8000/api/v1/cases', headers=headers, json={
    'case_name': 'Automated Test Case Beta',
    'case_type': 'FINANCIAL_FRAUD',
    'lead_investigator_id': 'USER-OFFICER-001',
    'description': 'End to end automated pipeline test.',
    'synopsis': 'End to end automated pipeline test.'
})
case_data = c_resp.json()
case_id = case_data['case_id']
print('Created Case:', case_id)

# 2. Register Evidence
ev_resp = requests.post(f'http://localhost:8000/api/v1/cases/{case_id}/evidence', headers=headers, data={
    'evidence_name': 'Test_Image3.E01',
    'evidence_type': 'DISK_IMAGE',
    'local_image_path': 'D:/Proto SIH/Test_Image3/Test_Image3.E01',
    'source_description': 'Main forensic image'
})
ev_data = ev_resp.json()
evidence_id = ev_data['evidence_id']
print('Registered Evidence:', evidence_id)

# 3. Trigger Processing
p_resp = requests.post(f'http://localhost:8000/api/v1/cases/{case_id}/evidence/{evidence_id}/process', headers=headers)
job_data = p_resp.json()
job_id = job_data['job_id']
print('Launched Processing Job:', job_id)

# 4. Poll until job completes
for _ in range(60):
    time.sleep(2)
    st = requests.get(f'http://localhost:8000/api/v1/processing/jobs/{job_id}', headers=headers).json()
    status = st.get('status')
    print('  Job status:', status)
    if status in ['COMPLETED', 'FAILED']:
        break

# 5. Verify Artifacts
arts = requests.get(f'http://localhost:8000/api/v1/cases/{case_id}/artifacts', headers=headers).json()
print(f'Total Artifacts Ingested: {len(arts)}')

# 6. Verify Graph
g = requests.get(f'http://localhost:8000/api/v1/cases/{case_id}/graph', headers=headers).json()
print('Knowledge Graph is_empty:', g.get('is_empty'))
print('Total Graph Nodes:', g.get('summary', {}).get('total_nodes'))
print('Total Graph Edges:', g.get('summary', {}).get('total_edges'))
