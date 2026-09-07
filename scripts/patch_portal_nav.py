"""
Patch build_final_workspace_html.py to:
1. Add class="workspace-nav-item" to all activity bar buttons EXCEPT home
2. In switchFeature('home'): hide workspace-nav-items + hide panel-console
3. In non-home switchFeature: show workspace-nav-items + show panel-console
"""

with open('scripts/build_final_workspace_html.py', 'r', encoding='utf-8') as f:
    content = f.read()

original_len = len(content)

# ─────────────────────────────────────────────────────────────
# PATCH 1: Add class="workspace-nav-item" to each non-home activity button
# ─────────────────────────────────────────────────────────────

patches_1 = [
    # Cases button
    (
        'class="activity-item" id="activity-btn-cases"',
        'class="activity-item workspace-nav-item" id="activity-btn-cases"'
    ),
    # Explorer button
    (
        'class="activity-item" id="activity-btn-explorer"',
        'class="activity-item workspace-nav-item" id="activity-btn-explorer"'
    ),
    # Network button
    (
        'class="activity-item" id="activity-btn-network"',
        'class="activity-item workspace-nav-item" id="activity-btn-network"'
    ),
    # Reports button
    (
        'class="activity-item" id="activity-btn-reports"',
        'class="activity-item workspace-nav-item" id="activity-btn-reports"'
    ),
    # Audit button
    (
        'class="activity-item" id="activity-btn-audit"',
        'class="activity-item workspace-nav-item" id="activity-btn-audit"'
    ),
]

for old, new in patches_1:
    if old in content:
        content = content.replace(old, new, 1)
        print(f'Patched: {old[:60]}...')
    else:
        print(f'WARNING: not found: {old[:60]}')

# ─────────────────────────────────────────────────────────────
# PATCH 2: In switchFeature home block — also hide workspace-nav-items and console
# ─────────────────────────────────────────────────────────────
# Find the home branch and add the extra hides

OLD_HOME_BLOCK = (
    "if (feature === 'home') {\\n"
    "                if (leftPanel) leftPanel.style.display = 'none';\\n"
    "                if (rightPanel) rightPanel.style.display = 'none';\\n"
    "                if (splitterLeft) splitterLeft.style.display = 'none';\\n"
    "                if (splitterRight) splitterRight.style.display = 'none';\\n"
    "                if (headerTools) headerTools.style.display = 'none';"
)
NEW_HOME_BLOCK = (
    "if (feature === 'home') {\\n"
    "                if (leftPanel) leftPanel.style.display = 'none';\\n"
    "                if (rightPanel) rightPanel.style.display = 'none';\\n"
    "                if (splitterLeft) splitterLeft.style.display = 'none';\\n"
    "                if (splitterRight) splitterRight.style.display = 'none';\\n"
    "                if (headerTools) headerTools.style.display = 'none';\\n"
    "                document.querySelectorAll('.workspace-nav-item').forEach(el => el.style.display = 'none');\\n"
    "                const consolePanel = document.getElementById('panel-console');\\n"
    "                if (consolePanel) consolePanel.style.display = 'none';"
)

if OLD_HOME_BLOCK in content:
    content = content.replace(OLD_HOME_BLOCK, NEW_HOME_BLOCK, 1)
    print('Patched: home block hides workspace-nav-items + console')
else:
    print('WARNING: home block pattern not found, trying looser search...')
    # Find by JS pattern in the raw content
    idx = content.find("if (feature === 'home')")
    if idx != -1:
        # Get the next 600 chars
        chunk = content[idx:idx+600]
        print('Found home block at idx=%d:' % idx)
        print(repr(chunk[:400]))
    else:
        print('ERROR: cannot find home feature block')

# ─────────────────────────────────────────────────────────────
# PATCH 3: In non-home else block — show workspace-nav-items + console
# ─────────────────────────────────────────────────────────────

OLD_ELSE_BLOCK = (
    "} else {\\n"
    "                if (leftPanel) leftPanel.style.display = '';\\n"
    "                if (rightPanel) rightPanel.style.display = '';\\n"
    "                if (splitterLeft) splitterLeft.style.display = '';\\n"
    "                if (splitterRight) splitterRight.style.display = '';\\n"
    "                if (headerTools) headerTools.style.display = 'flex';\\n"
    "            }"
)
NEW_ELSE_BLOCK = (
    "} else {\\n"
    "                if (leftPanel) leftPanel.style.display = '';\\n"
    "                if (rightPanel) rightPanel.style.display = '';\\n"
    "                if (splitterLeft) splitterLeft.style.display = '';\\n"
    "                if (splitterRight) splitterRight.style.display = '';\\n"
    "                if (headerTools) headerTools.style.display = 'flex';\\n"
    "                document.querySelectorAll('.workspace-nav-item').forEach(el => el.style.display = '');\\n"
    "                const consolePanel = document.getElementById('panel-console');\\n"
    "                if (consolePanel) consolePanel.style.display = '';\\n"
    "            }"
)

if OLD_ELSE_BLOCK in content:
    content = content.replace(OLD_ELSE_BLOCK, NEW_ELSE_BLOCK, 1)
    print('Patched: else block restores workspace-nav-items + console')
else:
    print('WARNING: else block pattern not found')

# ─────────────────────────────────────────────────────────────
# Save
# ─────────────────────────────────────────────────────────────
with open('scripts/build_final_workspace_html.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'\nDone. File size: {len(content)} bytes (was {original_len})')

# Verify
with open('scripts/build_final_workspace_html.py', 'r', encoding='utf-8') as f:
    v = f.read()

print('workspace-nav-item in content:', 'workspace-nav-item' in v)
print('panel-console hide in home block:', "panel-console" in v)
print('activity-btn-cases has workspace-nav-item:', 'workspace-nav-item" id="activity-btn-cases"' in v)
