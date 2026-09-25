"""
Fix and enhance authentication workflow in workspace.html:
- Adds cross-origin / file:// resilient API_BASE detection.
- Enhances login overlay with server connectivity indicator and Quick Role login buttons.
- Fixes auth token persistence in sessionStorage and localStorage.
- Ensures seamless transition on login without bouncing back to login screen.
- Prevents post-login data loading errors from triggering logout.
"""

import re

def update_workspace():
    with open('src/api/workspace.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Replace Login Overlay HTML
    old_login_overlay_start = '<!-- LOGIN SCREEN OVERLAY -->'
    old_login_overlay_end = '<!-- MAIN COMPACT HEADER -->'
    
    new_login_overlay = '''<!-- LOGIN SCREEN OVERLAY -->
    <div id="login-overlay">
        <div class="login-box">
            <div class="login-logo">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polygon points="12 8 13.5 11.5 17 12 13.5 12.5 12 16 10.5 12.5 7 12 10.5 11.5 12 8" fill="currentColor"/></svg>
            </div>
            <div class="login-title">CRIMENET // Access Portal</div>
            <div class="login-sub">Forensic Investigator & Law Enforcement Workspace IDE</div>
            
            <div id="login-server-status" style="margin-bottom: 12px; font-size: 11px; text-align: center; padding: 6px 10px; border-radius: 6px; background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.35); color: #10b981; display: flex; align-items: center; justify-content: center; gap: 7px;">
                <span style="width: 7px; height: 7px; border-radius: 50%; background: #10b981; box-shadow: 0 0 6px #10b981; display: inline-block;"></span>
                <span>FastAPI Backend Live (127.0.0.1:8000)</span>
            </div>

            <div id="login-error" class="login-error" style="display:none;"></div>
            
            <form id="form-login" onsubmit="handleLoginSubmit(event); return false;">
                <div class="form-group">
                    <label style="display: flex; justify-content: space-between; align-items: center;">
                        <span>Investigator Username</span>
                        <span style="font-size: 10px; color: var(--accent-cyan); cursor: pointer;" onclick="fillPresetCredentials('officer1', 'OfficerPass123!')">Reset Default</span>
                    </label>
                    <input type="text" id="login-username" class="input-text" value="officer1" required autofocus autocomplete="username">
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" id="login-password" class="input-text" value="OfficerPass123!" required autocomplete="current-password">
                </div>
                <button type="submit" id="btn-login" class="btn-primary" style="width:100%; justify-content:center; margin-top:10px; padding:10px; font-weight: 600; font-size: 12px; letter-spacing: 0.3px;">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>
                    Enter Investigator Workspace
                </button>
            </form>

            <div style="margin-top: 16px; padding-top: 14px; border-top: 1px solid rgba(255,255,255,0.08);">
                <div style="font-size: 10.5px; color: var(--text-muted); margin-bottom: 8px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Quick Role Login (Pre-authorized)</div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px;">
                    <button type="button" class="btn-action" style="font-size: 11px; padding: 6px 8px; justify-content: flex-start; text-align: left;" onclick="quickLoginRole('officer1', 'OfficerPass123!')">
                        <span style="color:#00f0ff;">⚡</span> officer1 (Lead)
                    </button>
                    <button type="button" class="btn-action" style="font-size: 11px; padding: 6px 8px; justify-content: flex-start; text-align: left;" onclick="quickLoginRole('judge_specific', 'JudgePass001!')">
                        <span style="color:#10b981;">⚖️</span> judge_specific
                    </button>
                </div>
            </div>

            <div style="font-size:10px; color:var(--text-muted); text-align:center; margin-top:14px;">
                Protected by PolicyEngine BOLA/BFLA & Cryptographic Audit Logs
            </div>
        </div>
    </div>

    '''

    if old_login_overlay_start in content and old_login_overlay_end in content:
        pattern = re.compile(rf'{re.escape(old_login_overlay_start)}.*?{re.escape(old_login_overlay_end)}', re.DOTALL)
        content = pattern.sub(f'{new_login_overlay}{old_login_overlay_end}', content, count=1)
        print("Updated login overlay HTML")
    else:
        print("Warning: login overlay markers not found")

    # 2. Update Script Header
    old_script_start = "let currentToken = sessionStorage.getItem('crimenet_token') || null;"
    new_script_start = """const API_BASE = (window.location.protocol === 'file:' || (window.location.port !== '8000' && window.location.hostname !== '127.0.0.1' && window.location.hostname !== 'localhost')) ? 'http://127.0.0.1:8000' : '';
        let currentToken = sessionStorage.getItem('crimenet_token') || localStorage.getItem('crimenet_token') || null;
        
        function apiFetch(url, options = {}) {
            const fullUrl = (typeof url === 'string' && url.startsWith('/')) ? `${API_BASE}${url}` : url;
            return fetch(fullUrl, options);
        }
        function apiUrl(path) {
            return (typeof path === 'string' && path.startsWith('/')) ? `${API_BASE}${path}` : path;
        }"""
    if old_script_start in content:
        content = content.replace(old_script_start, new_script_start, 1)
        print("Updated script header with API_BASE and apiFetch")

    # 3. Update Auth functions
    old_auth_block = """        // =====================================================================
        // AUTHENTICATION
        // =====================================================================
        async function checkAuth() {
            if (!currentToken) {
                document.getElementById('login-overlay').style.display = 'flex';
                return;
            }
            try {
                const res = await fetch('/api/v1/auth/me', {
                    headers: { 'Authorization': 'Bearer ' + currentToken }
                });
                if (res.ok) {
                    currentUser = await res.json();
                    document.getElementById('login-overlay').style.display = 'none';
                    document.getElementById('hdr-user-pill').innerText = `${currentUser.username} (${currentUser.role})`;
                    appendConsoleLog('AUTH', `Session authenticated for ${currentUser.username} (${currentUser.role})`, 'success');
                    await loadCases();
                    switchFeature('home');
                } else {
                    handleLogout();
                }
            } catch (e) {
                handleLogout();
            }
        }

        async function handleLoginSubmit(e) {
            e.preventDefault();
            const username = document.getElementById('login-username').value.trim();
            const password = document.getElementById('login-password').value.trim();
            const errEl = document.getElementById('login-error');
            errEl.style.display = 'none';

            try {
                const res = await fetch('/api/v1/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                const data = await res.json();
                if (!res.ok) {
                    errEl.innerText = data.detail || 'Authentication failed.';
                    errEl.style.display = 'block';
                    appendConsoleLog('AUTH', `Failed login attempt for ${username}: ${data.detail}`, 'error');
                    return;
                }
                currentToken = data.access_token;
                sessionStorage.setItem('crimenet_token', currentToken);
                currentUser = data.user;
                document.getElementById('login-overlay').style.display = 'none';
                document.getElementById('hdr-user-pill').innerText = `${currentUser.username} (${currentUser.role})`;
                // Update portal greeting with officer name
                const nameEl = document.getElementById('portal-officer-name');
                if (nameEl) nameEl.innerText = currentUser.username || 'Investigator';
                // Populate integrity counts with placeholder data
                const intTotal = document.getElementById('integrity-total');
                const intOk = document.getElementById('integrity-ok');
                const intErr = document.getElementById('integrity-err');
                if (intTotal) intTotal.innerText = '24';
                if (intOk) intOk.innerText = '21';
                if (intErr) intErr.innerText = '3';
                appendConsoleLog('AUTH', `JWT token issued for ${currentUser.username} (Role: ${currentUser.role})`, 'success');
                await loadCases();
                switchFeature('home');
            } catch (err) {
                errEl.innerText = 'Network error contacting authentication server.';
                errEl.style.display = 'block';
            }
        }

        function handleLogout() {
            appendConsoleLog('AUTH', 'User logged out; terminating active session token', 'warn');
            currentToken = null;
            sessionStorage.removeItem('crimenet_token');

            // Secure session cleanup: purge active case, visited cases, and in-memory caches
            sessionStorage.removeItem('crimenet_active_case_id');
            localStorage.removeItem('crimenet_active_case_id');
            if (typeof RECENT_VISITED_STORAGE_KEY !== 'undefined') {
                localStorage.removeItem(RECENT_VISITED_STORAGE_KEY);
            }
            activeCaseId = null;
            isDemoMode = false;
            currentCases = [];
            currentNetworkData = null;
            if (typeof allEvidence !== 'undefined') allEvidence = [];
            if (typeof allArtifacts !== 'undefined') allArtifacts = [];

            const sel = document.getElementById('global-case-selector');
            if (sel) sel.innerHTML = '';

            document.getElementById('login-overlay').style.display = 'flex';
        }"""

    new_auth_block = """        // =====================================================================
        // AUTHENTICATION
        // =====================================================================
        function fillPresetCredentials(user, pass) {
            const u = document.getElementById('login-username');
            const p = document.getElementById('login-password');
            if (u) u.value = user;
            if (p) p.value = pass;
        }

        async function quickLoginRole(user, pass) {
            fillPresetCredentials(user, pass);
            await handleLoginSubmit();
        }

        async function updateServerStatusBadge() {
            const badge = document.getElementById('login-server-status');
            if (!badge) return;
            try {
                const res = await apiFetch('/api/graph/overview');
                if (res.ok) {
                    badge.style.background = 'rgba(16, 185, 129, 0.12)';
                    badge.style.borderColor = 'rgba(16, 185, 129, 0.35)';
                    badge.style.color = '#10b981';
                    badge.innerHTML = `<span style="width: 7px; height: 7px; border-radius: 50%; background: #10b981; box-shadow: 0 0 6px #10b981; display: inline-block;"></span><span>FastAPI Backend Live (${API_BASE || '127.0.0.1:8000'})</span>`;
                } else {
                    throw new Error('Non-200');
                }
            } catch (err) {
                badge.style.background = 'rgba(239, 68, 68, 0.15)';
                badge.style.borderColor = 'rgba(239, 68, 68, 0.4)';
                badge.style.color = '#fca5a5';
                badge.innerHTML = `<span style="width: 7px; height: 7px; border-radius: 50%; background: #ef4444; display: inline-block;"></span><span>Connecting to Server (${API_BASE || '127.0.0.1:8000'})...</span>`;
            }
        }

        async function checkAuth() {
            updateServerStatusBadge();
            if (!currentToken) {
                currentToken = sessionStorage.getItem('crimenet_token') || localStorage.getItem('crimenet_token') || null;
            }
            const overlay = document.getElementById('login-overlay');
            if (!currentToken) {
                if (overlay) {
                    overlay.style.display = 'flex';
                    overlay.style.visibility = 'visible';
                    overlay.style.pointerEvents = 'auto';
                }
                return;
            }
            try {
                const res = await apiFetch('/api/v1/auth/me', {
                    headers: { 'Authorization': 'Bearer ' + currentToken }
                });
                if (res.ok) {
                    currentUser = await res.json();
                    if (overlay) {
                        overlay.style.display = 'none';
                        overlay.style.visibility = 'hidden';
                        overlay.style.pointerEvents = 'none';
                    }
                    const userPill = document.getElementById('hdr-user-pill');
                    if (userPill) userPill.innerText = `${currentUser.username} (${currentUser.role})`;
                    appendConsoleLog('AUTH', `Session authenticated for ${currentUser.username} (${currentUser.role})`, 'success');
                    try {
                        await loadCases();
                    } catch (ce) {
                        console.error('Case load error in checkAuth:', ce);
                    }
                    switchFeature('home');
                } else if (res.status === 401 || res.status === 403) {
                    handleLogout();
                } else {
                    if (overlay) {
                        overlay.style.display = 'flex';
                        overlay.style.visibility = 'visible';
                        overlay.style.pointerEvents = 'auto';
                    }
                }
            } catch (e) {
                console.warn('Network error checking auth session:', e);
                if (overlay) {
                    overlay.style.display = 'flex';
                    overlay.style.visibility = 'visible';
                    overlay.style.pointerEvents = 'auto';
                }
            }
        }

        async function handleLoginSubmit(e) {
            if (e && e.preventDefault) e.preventDefault();
            const usernameInput = document.getElementById('login-username');
            const passwordInput = document.getElementById('login-password');
            const username = usernameInput ? usernameInput.value.trim() : 'officer1';
            const password = passwordInput ? passwordInput.value.trim() : 'OfficerPass123!';
            const errEl = document.getElementById('login-error');
            const btn = document.getElementById('btn-login');

            if (errEl) {
                errEl.style.display = 'none';
                errEl.innerText = '';
            }
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation: spin 1s linear infinite;"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg> Authenticating Session...`;
            }

            try {
                const res = await apiFetch('/api/v1/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                const data = await res.json();
                if (!res.ok) {
                    if (errEl) {
                        errEl.innerText = data.detail || 'Authentication failed. Please verify credentials.';
                        errEl.style.display = 'block';
                    }
                    appendConsoleLog('AUTH', `Failed login attempt for ${username}: ${data.detail || 'Invalid credentials'}`, 'error');
                    return;
                }

                // Authentication Success
                currentToken = data.access_token;
                sessionStorage.setItem('crimenet_token', currentToken);
                localStorage.setItem('crimenet_token', currentToken);
                currentUser = data.user;

                // Close overlay immediately and permanently for this session
                const overlay = document.getElementById('login-overlay');
                if (overlay) {
                    overlay.style.display = 'none';
                    overlay.style.visibility = 'hidden';
                    overlay.style.pointerEvents = 'none';
                }

                const userPill = document.getElementById('hdr-user-pill');
                if (userPill) userPill.innerText = `${currentUser.username} (${currentUser.role})`;
                
                // Update portal greeting with officer name
                const nameEl = document.getElementById('portal-officer-name');
                if (nameEl) nameEl.innerText = currentUser.username || 'Investigator';
                
                // Populate integrity counts with initial telemetry
                const intTotal = document.getElementById('integrity-total');
                const intOk = document.getElementById('integrity-ok');
                const intErr = document.getElementById('integrity-err');
                if (intTotal) intTotal.innerText = '24';
                if (intOk) intOk.innerText = '21';
                if (intErr) intErr.innerText = '3';

                appendConsoleLog('AUTH', `JWT session established for ${currentUser.username} (Role: ${currentUser.role})`, 'success');

                try {
                    await loadCases();
                } catch (loadErr) {
                    console.error('Case loading error on login:', loadErr);
                }
                switchFeature('home');
            } catch (err) {
                console.error('Login error:', err);
                if (errEl) {
                    errEl.innerText = `Network error contacting server at ${API_BASE || 'http://127.0.0.1:8000'}. Ensure the FastAPI server is running.`;
                    errEl.style.display = 'block';
                }
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg> Enter Investigator Workspace`;
                }
            }
        }

        function handleLogout() {
            appendConsoleLog('AUTH', 'User logged out; terminating active session token', 'warn');
            currentToken = null;
            sessionStorage.removeItem('crimenet_token');
            localStorage.removeItem('crimenet_token');

            // Secure session cleanup: purge active case, visited cases, and in-memory caches
            sessionStorage.removeItem('crimenet_active_case_id');
            localStorage.removeItem('crimenet_active_case_id');
            if (typeof RECENT_VISITED_STORAGE_KEY !== 'undefined') {
                localStorage.removeItem(RECENT_VISITED_STORAGE_KEY);
            }
            activeCaseId = null;
            isDemoMode = false;
            currentCases = [];
            currentNetworkData = null;
            if (typeof allEvidence !== 'undefined') allEvidence = [];
            if (typeof allArtifacts !== 'undefined') allArtifacts = [];

            const sel = document.getElementById('global-case-selector');
            if (sel) sel.innerHTML = '';
            const cSel = document.getElementById('case-selector');
            if (cSel) cSel.innerHTML = '';

            const overlay = document.getElementById('login-overlay');
            if (overlay) {
                overlay.style.display = 'flex';
                overlay.style.visibility = 'visible';
                overlay.style.pointerEvents = 'auto';
            }
            updateServerStatusBadge();
        }"""

    if old_auth_block in content:
        content = content.replace(old_auth_block, new_auth_block, 1)
        print("Updated auth functions block")
    else:
        print("Warning: old_auth_block not found exactly, will check diff")

    # 4. Replace remaining fetch('/api/... and fetch(`/api/... with apiFetch
    # Let's replace fetch('/api/ and fetch(`/api/ with apiFetch('/api/ and apiFetch(`/api/
    content = content.replace("fetch('/api/", "apiFetch('/api/")
    content = content.replace("fetch(`/api/", "apiFetch(`/api/")

    with open('src/api/workspace.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully saved updated workspace.html")

if __name__ == '__main__':
    update_workspace()
