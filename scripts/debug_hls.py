import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open('scripts/build_final_workspace_html.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('async function handleLoginSubmit')
if idx != -1:
    chunk = content[idx:idx+2000]
    success_idx = chunk.find('currentUser = data.user')
    if success_idx != -1:
        print('Success branch (raw):')
        # Show a larger window
        raw = chunk[success_idx:success_idx+600]
        print(repr(raw))
        print('\n---\nLoadCases present:', 'loadCases' in raw)
        print("switchFeature home present:", "switchFeature('home')" in raw)
