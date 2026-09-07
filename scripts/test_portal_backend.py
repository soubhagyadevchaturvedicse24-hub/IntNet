import urllib.request, json

data = json.dumps({'username': 'officer1', 'password': 'OfficerPass123!'}).encode()
req = urllib.request.Request('http://127.0.0.1:8000/api/v1/auth/login', data=data, headers={'Content-Type': 'application/json'})
tok = json.loads(urllib.request.urlopen(req).read())['access_token']
h = {'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json'}

# Test judges
res = urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8000/api/v1/judicial/judges', headers=h))
judges = json.loads(res.read())
print('Judges (%d): %s' % (len(judges), [j['username'] for j in judges]))

# Test candidates
res = urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8000/api/v1/evidence/candidates', headers=h))
cands = json.loads(res.read())
print('Candidates (%d): %s' % (len(cands), [c['candidate_id'] for c in cands]))

# Test inspect (strictly read-only)
data2 = json.dumps({'candidate_id': 'cand_images_set_1'}).encode()
res = urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8000/api/v1/evidence/inspect', data=data2, headers=h))
d = json.loads(res.read())
print('Inspect: valid=%s, format=%s, segments=%s, examiner=%s' % (d['valid'], d['format'], d['segments'], d['examiner_name']))

# Test workspace HTML 
res = urllib.request.urlopen('http://127.0.0.1:8000/')
html = res.read().decode('utf-8')
checks = [
    ('view-portal', 'id="view-portal"'),
    ('activity-btn-home', 'activity-btn-home'),
    ('modal-new-case-flow', 'modal-new-case-flow'),
    ('modal-all-cases', 'modal-all-cases'),
    ('INVESTIGATOR CASE PORTAL', 'INVESTIGATOR CASE PORTAL'),
    ('renderPortalRecentCases', 'renderPortalRecentCases'),
    ('executeNewCaseCreation', 'executeNewCaseCreation'),
    ('openNewCaseModal', 'openNewCaseModal'),
    ('switchFeature home', "switchFeature('home')"),
]
print('Workspace HTML size: %d bytes' % len(html))
for name, needle in checks:
    print('  %s: %s' % (name, 'OK' if needle in html else 'MISSING'))
