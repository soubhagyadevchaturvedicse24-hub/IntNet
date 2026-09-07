import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open('src/api/workspace.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find handleLoginSubmit in the compiled HTML
idx = html.find('async function handleLoginSubmit')
if idx != -1:
    chunk = html[idx:idx+1800]
    print('=== handleLoginSubmit (compiled HTML) ===')
    print(chunk)

print('\n\n=== checkAuth (compiled HTML) ===')
idx2 = html.find('async function checkAuth')
if idx2 != -1:
    print(html[idx2:idx2+800])
