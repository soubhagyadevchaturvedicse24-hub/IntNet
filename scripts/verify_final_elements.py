with open('src/api/workspace.html', 'r', encoding='utf-8') as f:
    html = f.read()

print('artifact-bottom-panel in HTML tags:', 'class="artifact-bottom-panel"' in html)
print('artifact-tab-bar in HTML tags:', 'class="artifact-tab-bar"' in html)
print('console-resize-handle count:', html.count('console-resize-handle'))
print('btab-btn-art- count:', html.count('btab-btn-art-'))
print('bottom-pane-art- count:', html.count('bottom-pane-art-'))

# Check tab button IDs in bottom tabs
tabs = ['meta', 'attrs', 'console', 'art-meta', 'art-parsed', 'art-text', 'art-hex', 'art-raw']
for t in tabs:
    btn_id = f'id="btab-btn-{t}"'
    pane_id = f'id="bottom-pane-{t}"'
    print(f'Tab {t}: btn={btn_id in html}, pane={pane_id in html}')
