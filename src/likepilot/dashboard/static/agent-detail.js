(() => {
    const root = document.getElementById('agent-detail');
    if (!root) return;
    const name = root.dataset.agentName;
    const byId = (id) => document.getElementById(id);
    const safe = (value) => String(value ?? '—').replace(/[&<>"']/g, (char) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[char]));
    const set = (id, value) => { const node = byId(id); if (node) node.textContent = value || '—'; };

    async function loadAgent() {
        const response = await fetch('/api/status', { headers: { Accept: 'application/json' } });
        if (!response.ok) throw new Error('Unable to load agent status.');
        const payload = await response.json();
        const agent = payload.agents?.[name];
        if (!agent) {
            set('agent-summary', 'This agent no longer exists or is not available.');
            set('agent-status', 'Not found');
            return;
        }
        set('agent-name', name);
        set('agent-summary', [agent.site, agent.platform].filter(Boolean).join(' · ') || 'Agent runtime');
        const badge = byId('agent-status');
        badge.textContent = agent.status || 'Unknown';
        badge.className = 'status-badge status-' + String(agent.status || 'unknown').toLowerCase().replace(/[^a-z0-9]+/g, '-');
        set('agent-credits', agent.credits);
        set('agent-gain', (Number(agent.session_gain) >= 0 ? '+' : '') + Number(agent.session_gain || 0));
        set('agent-peak', agent.session_peak);
        set('agent-samples', agent.samples);
        set('agent-provider', agent.site);
        set('agent-platform', agent.platform);
        set('agent-profile', agent.chrome_profile);
        set('agent-proxy', agent.proxy || 'Not configured');
        set('agent-fallback', agent.fallback_chain || agent.fallback_platform || 'None');
        set('agent-heartbeat', agent.heartbeat_at);
        set('agent-session-start', agent.session_started_at);
        const events = byId('agent-event-list');
        const logs = Array.isArray(agent.logs) ? agent.logs : [];
        events.innerHTML = logs.length ? logs.map((item) => {
            const line = String(item);
            const match = line.match(/^(.*?) \\[([^\\]]+)\\] (.*)$/);
            const timestamp = match ? match[1] : '';
            const level = match ? match[2] : 'INFO';
            const message = match ? match[3] : line;
            return '<article class="event-row"><div class="event-row-meta"><span class="event-level">' +
                safe(level) + '</span><time>' + safe(timestamp) +
                '</time></div><p>' + safe(message) + '</p></article>';
        }).join('') : '<div class="empty-state">No recent events for this agent.</div>';
        root.querySelectorAll('[data-agent-action]').forEach((button) => {
            const action = button.dataset.agentAction;
            button.hidden = (action === 'ready' && !['Awaiting Login', 'Login Success'].includes(agent.status)) ||
                (action === 'initialize' && agent.status !== 'Login Success');
            button.disabled = (action === 'start' && agent.status !== 'Stopped') ||
                (action === 'ready' && !['Awaiting Login', 'Login Success'].includes(agent.status)) ||
                (action === 'initialize' && agent.status !== 'Login Success') ||
                (action === 'pause' && agent.status !== 'Running') ||
                (action === 'resume' && agent.status !== 'Paused') ||
                (action === 'stop' && agent.status === 'Stopped');
        });
        const platformSelect = byId('agent-platform-select');
        if (platformSelect) platformSelect.value = agent.platform || 'Twitter';
        const confirmPlatform = byId('agent-confirm-platform');
        if (confirmPlatform) confirmPlatform.hidden = !agent.switch_pending;
        if (platformSelect) platformSelect.hidden = !agent.switch_pending;
        const error = byId('agent-error');
        if (agent.last_error) { error.hidden = false; error.textContent = agent.last_error; }
        else { error.hidden = true; }
    }

    root.querySelectorAll('[data-agent-action]').forEach((button) => {
        button.addEventListener('click', async () => {
            const action = button.dataset.agentAction;
            button.disabled = true;
            try {
                const response = await fetch('/api/control', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, action })
                });
                const result = await response.json();
                if (!response.ok) throw new Error(result.message || 'Command failed.');
                window.showNotification?.(result.message || 'Agent command sent.', 'success');
                await loadAgent();
            } catch (error) {
                window.showNotification?.(error.message, 'error');
                button.disabled = false;
            }
        });
    });

    byId('agent-confirm-platform')?.addEventListener('click', async () => {
        const platform = byId('agent-platform-select')?.value;
        try {
            const response = await fetch('/api/platform', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, platform })
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.message || 'Platform update failed.');
            window.showNotification?.(result.message || 'Platform updated.', 'success');
            await loadAgent();
        } catch (error) { window.showNotification?.(error.message, 'error'); }
    });

    loadAgent().catch((error) => {
        set('agent-summary', error.message);
        window.showNotification?.(error.message, 'error');
    });
    window.setInterval(() => loadAgent().catch(() => {}), 5000);
})();