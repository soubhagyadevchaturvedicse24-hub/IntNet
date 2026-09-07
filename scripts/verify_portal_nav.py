import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open('src/api/workspace.html', 'r', encoding='utf-8') as f:
    html = f.read()

idx = html.find("function switchFeature(feature)")
if idx != -1:
    chunk = html[idx:idx+1500]
    print(chunk)
