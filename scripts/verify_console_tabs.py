import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open('src/api/workspace.html', 'r', encoding='utf-8') as f:
    html = f.read()

checks = [
    # Console has 5 new artifact tabs
    ('btab-btn-art-meta present', 'btab-btn-art-meta' in html),
    ('btab-btn-art-parsed present', 'btab-btn-art-parsed' in html),
    ('btab-btn-art-text present', 'btab-btn-art-text' in html),
    ('btab-btn-art-hex present', 'btab-btn-art-hex' in html),
    ('btab-btn-art-raw present', 'btab-btn-art-raw' in html),
    # Console panes present
    ('bottom-pane-art-meta present', 'bottom-pane-art-meta' in html),
    ('bottom-pane-art-parsed present', 'bottom-pane-art-parsed' in html),
    ('bottom-pane-art-text present', 'bottom-pane-art-text' in html),
    ('bottom-pane-art-hex present', 'bottom-pane-art-hex' in html),
    ('bottom-pane-art-raw present', 'bottom-pane-art-raw' in html),
    # artifact-bottom-panel REMOVED from center
    ('artifact-bottom-panel removed', 'artifact-bottom-panel' not in html),
    ('artifact-tab-bar removed', 'artifact-tab-bar' not in html),
    # Resize handle present
    ('console-resize-handle div', 'console-resize-handle' in html),
    ('initConsoleResize JS', 'initConsoleResize' in html),
    # Tab separator present
    ('bottom-tabs-sep present', 'bottom-tabs-sep' in html),
    # switchArtifactBottomTab still works
    ('switchArtifactBottomTab defined', 'function switchArtifactBottomTab' in html),
    # Auto-switch on artifact open
    ("switchBottomTab art-meta on open", "switchBottomTab('art-meta')" in html),
]

print(f'workspace.html size: {len(html):,} bytes')
for name, result in checks:
    status = 'OK' if result else 'FAIL'
    print(f'  [{status}] {name}')
