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
        events.innerHTML = logs.length ? logs.map((item) =>
            '<article class="event-row"><div class="event-row-meta"><span class="event-level">' +
            safe(item.level || 'INFO') + '</span><time>' + safe(item.created_at || '') +
            '</time></div><p>' + safe(item.message || '') + '</p></article>'
        ).join('') : '<div class="empty-state">No recent events for this agent.</div>';
        root.querySelectorAll('[data-agent-action]').forEach((button) => {
            const action = button.dataset.agentAction;
            button.disabled = (action === 'start' && !['Stopped'].includes(agent.status)) ||
                (action === 'pause' && agent.status !== 'Running') ||
                (action === 'resume' && agent.status !== 'Paused') ||
                (action === 'stop' && agent.status === 'Stopped');
        });
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

    loadAgent().catch((error) => {
        set('agent-summary', error.message);
        window.showNotification?.(error.message, 'error');
    });
    window.setInterval(() => loadAgent().catch(() => {}), 5000);
})();