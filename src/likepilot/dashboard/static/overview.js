(() => {
    const body = document.getElementById('overview-agent-rows');
    if (!body) return;

    const activityList = document.getElementById('overview-activity-list');
    const escape = (value) => String(value ?? '—').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const statusClass = (status) => 'status-' + String(status || 'unknown').toLowerCase().replace(/[^a-z0-9]+/g, '-');
    const waitingStates = ['Awaiting Login', 'Login Success', 'Awaiting Switch', 'Paused'];

    function parseLog(line) {
        const value = String(line || '');
        const match = value.match(/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\s+\[([^\]]+)\]\s*(.*)$/);
        if (!match) return { timestamp: 0, level: 'INFO', message: value };
        const parsed = Date.parse(match[1]);
        return { timestamp: Number.isNaN(parsed) ? 0 : parsed, level: match[2], message: match[3] };
    }

    function relativeTime(timestamp) {
        if (!timestamp) return 'No recent activity';
        const seconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
        if (seconds < 60) return 'Just now';
        if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
        if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago';
        return Math.floor(seconds / 86400) + 'd ago';
    }

    function renderActivity(agents) {
        const events = [];
        Object.entries(agents).forEach(([name, agent]) => {
            (agent.logs || []).forEach((line) => {
                const parsed = parseLog(line);
                if (parsed.message) events.push({ name, ...parsed, status: agent.status });
            });
        });
        events.sort((a, b) => b.timestamp - a.timestamp);
        const recent = events.slice(0, 12);
        document.getElementById('overview-activity-count').textContent = recent.length + (recent.length === 1 ? ' event' : ' events');
        activityList.innerHTML = recent.length ? recent.map((event) => {
            const message = event.message.replace(/^\[[^\]]+\]\s*/, '');
            const label = event.level.toLowerCase() === 'error' ? 'Error' : event.level.toLowerCase() === 'warning' ? 'Warning' : 'Update';
            return `<li class="overview-activity-item">
                <span class="overview-activity-mark ${event.level.toLowerCase() === 'error' ? 'is-error' : event.level.toLowerCase() === 'warning' ? 'is-warning' : ''}" aria-hidden="true"></span>
                <div class="overview-activity-copy">
                    <div class="overview-activity-meta"><a href="/agents/${encodeURIComponent(event.name)}">${escape(event.name)}</a><span>${escape(label)}</span></div>
                    <p>${escape(message)}</p>
                    <time>${escape(relativeTime(event.timestamp))}</time>
                </div>
            </li>`;
        }).join('') : '<li class="overview-activity-empty">No agent events have been recorded yet.</li>';
    }

    async function refresh() {
        const response = await fetch('/api/status', { headers: { Accept: 'application/json' } });
        if (!response.ok) throw new Error('Runtime status could not be loaded.');
        const payload = await response.json();
        const entries = Object.entries(payload.agents || {});
        const agents = entries.map(([, agent]) => agent);
        const running = agents.filter((agent) => agent.status === 'Running').length;
        const waiting = agents.filter((agent) => waitingStates.includes(agent.status)).length;
        const stopped = agents.filter((agent) => agent.status === 'Stopped').length;

        document.getElementById('overview-total').textContent = agents.length;
        document.getElementById('overview-running').textContent = running;
        document.getElementById('overview-waiting').textContent = waiting;
        document.getElementById('overview-stopped').textContent = stopped;

        const workspaceState = document.getElementById('overview-workspace-state');
        workspaceState.textContent = running ? 'Operational' : waiting ? 'Attention needed' : 'Idle';
        workspaceState.className = 'overview-workspace-status ' + (running ? 'is-running' : waiting ? 'is-waiting' : 'is-idle');

        body.innerHTML = entries.length ? entries.map(([name, agent]) => {
            const latestLog = (agent.logs || []).slice(-1)[0];
            const logTime = latestLog ? parseLog(latestLog).timestamp : Date.parse(agent.heartbeat_at || '');
            return `<tr>
                <td><a class="directory-agent-link" href="/agents/${encodeURIComponent(name)}">${escape(name)}</a></td>
                <td><span class="status-badge ${statusClass(agent.status)}">${escape(agent.status)}</span></td>
                <td>${escape(agent.site)}</td>
                <td>${escape(agent.platform)}</td>
                <td class="mono">${escape(agent.credits)}</td>
                <td class="section-subtle">${escape(relativeTime(logTime))}</td>
            </tr>`;
        }).join('') : '<tr><td colspan="6" class="section-subtle">No agents configured. Create an agent to get started.</td></tr>';

        renderActivity(payload.agents || {});
        document.getElementById('overview-updated').textContent = 'Updated ' + new Date().toLocaleTimeString();
        document.getElementById('overview-error').hidden = true;
    }

    function showError(error) {
        const node = document.getElementById('overview-error');
        node.hidden = false;
        node.textContent = error.message || 'Runtime status unavailable.';
        body.innerHTML = '<tr><td colspan="6" class="section-subtle">Runtime status unavailable.</td></tr>';
        activityList.innerHTML = '<li class="overview-activity-empty">Activity is unavailable while the runtime is disconnected.</li>';
    }

    refresh().catch(showError);
    window.setInterval(() => refresh().catch(() => {}), 5000);
})();
