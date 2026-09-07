"""
Fix the login/checkAuth landing to go to switchFeature('home') instead of initWorkspace().
Patches build_final_workspace_html.py directly, then recompiles workspace.html.
"""

import re

build_path = 'scripts/build_final_workspace_html.py'
with open(build_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Patch 1: handleLoginSubmit — after setting currentUser, replace initWorkspace() call
# The pattern: currentUser = data.user;  ...  initWorkspace();
# We replace just the initWorkspace() call that follows that block
OLD1 = (
    "currentUser = data.user;\\n"
    "                document.getElementById('login-overlay').style.display = 'none';\\n"
    "                document.getElementById('hdr-user-pill').innerText = `${currentUser.username} (${currentUser.role})`;\\n"
    "                appendConsoleLog('AUTH', `JWT token issued for ${currentUser.username} (Role: ${currentUser.role})`, 'success');\\n"
    "                initWorkspace();"
)
NEW1 = (
    "currentUser = data.user;\\n"
    "                document.getElementById('login-overlay').style.display = 'none';\\n"
    "                document.getElementById('hdr-user-pill').innerText = `${currentUser.username} (${currentUser.role})`;\\n"
    "                appendConsoleLog('AUTH', `JWT token issued for ${currentUser.username} (Role: ${currentUser.role})`, 'success');\\n"
    "                await loadCases();\\n"
    "                switchFeature('home');"
)

if OLD1 in content:
    content = content.replace(OLD1, NEW1, 1)
    print('Patched handleLoginSubmit landing -> home')
else:
    print('WARNING: handleLoginSubmit pattern not found, trying fallback...')
    # Fallback: find initWorkspace() inside handleLoginSubmit context
    # Find location of handleLoginSubmit
    hls_idx = content.find('async function handleLoginSubmit')
    if hls_idx == -1:
        hls_idx = content.find('function handleLoginSubmit')
    if hls_idx != -1:
        # Look for initWorkspace() within the next 2000 chars
        sub = content[hls_idx:hls_idx+2000]
        if 'initWorkspace();' in sub:
            first_call = sub.index('initWorkspace();')
            old_pos = hls_idx + first_call
            content = content[:old_pos] + "await loadCases();\\n                switchFeature('home');" + content[old_pos + len('initWorkspace();'):]
            print('Patched handleLoginSubmit landing via fallback')
        else:
            print('ERROR: Could not find initWorkspace() in handleLoginSubmit')

# Patch 2: checkAuth — after setting currentUser from /auth/me, replace initWorkspace() 
OLD2 = (
    "appendConsoleLog('AUTH', `Session authenticated for ${currentUser.username} (${currentUser.role})`, 'success');\\n"
    "                    initWorkspace();"
)
NEW2 = (
    "appendConsoleLog('AUTH', `Session authenticated for ${currentUser.username} (${currentUser.role})`, 'success');\\n"
    "                    await loadCases();\\n"
    "                    switchFeature('home');"
)

if OLD2 in content:
    content = content.replace(OLD2, NEW2, 1)
    print('Patched checkAuth landing -> home')
else:
    print('WARNING: checkAuth pattern not found, trying fallback...')
    ca_idx = content.find('async function checkAuth')
    if ca_idx == -1:
        ca_idx = content.find('function checkAuth')
    if ca_idx != -1:
        sub = content[ca_idx:ca_idx+2000]
        if 'initWorkspace();' in sub:
            first_call = sub.index('initWorkspace();')
            old_pos = ca_idx + first_call
            content = content[:old_pos] + "await loadCases();\\n                    switchFeature('home');" + content[old_pos + len('initWorkspace();'):]
            print('Patched checkAuth landing via fallback')
        else:
            print('ERROR: Could not find initWorkspace() in checkAuth')

with open(build_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Done patching build script.')

# Verify
with open(build_path, 'r', encoding='utf-8') as f:
    verify = f.read()

hls_idx = verify.find('async function handleLoginSubmit')
sub_hls = verify[hls_idx:hls_idx+1500] if hls_idx != -1 else ''
ca_idx = verify.find('async function checkAuth')
sub_ca = verify[ca_idx:ca_idx+1000] if ca_idx != -1 else ''

print('\nhandleLoginSubmit has switchFeature home:', "switchFeature('home')" in sub_hls)
print('handleLoginSubmit has initWorkspace:', 'initWorkspace()' in sub_hls)
print('checkAuth has switchFeature home:', "switchFeature('home')" in sub_ca)
print('checkAuth has initWorkspace:', 'initWorkspace()' in sub_ca)
