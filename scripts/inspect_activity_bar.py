import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open('src/api/workspace.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find console panel/footer
for needle in ['id="console-', 'id="footer-', 'id="bottom-', 'class="console', 'panel-console', 'console-panel']:
    idx = html.find(needle)
    if idx != -1:
        print(f'=== Found "{needle}" at {idx} ===')
        print(html[idx:idx+300])
        print()
