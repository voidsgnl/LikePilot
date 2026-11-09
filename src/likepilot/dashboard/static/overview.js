(() => {
    const activityList = document.getElementById('overview-activity-list');
    if (!activityList) return;
    const escape = (value) => String(value ?? '—').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const waitingStates = ['Awaiting Login', 'Login Success', 'Awaiting Social Login', 'Awaiting Switch', 'Paused'];

    function parseLog(line) {
        const value = String(line || '');
        const match = value.match(/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\s+\[([^\]]+)\]\s*(.*)$/);
        if (!match) return { timestamp: 0, level: 'INFO', message: value };
        const parsed = Date.parse(match[1]);
        return { timestamp: Number.isNaN(parsed) ? 0 : parsed, level: match[2], message: match[3] };
    }

    function relativeTime(timestamp) {
        if (!timestamp) return 'Time unavailable';
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
                if (parsed.message) events.push({ name, ...parsed });
            });
        });
        events.sort((a, b) => b.timestamp - a.timestamp);
        const recent = events.slice(0, 5);
        document.getElementById('overview-activity-count').textContent = recent.length + (recent.length === 1 ? ' event' : ' events');
        activityList.innerHTML = recent.length ? recent.map((event) => {
            const level = event.level.toLowerCase();
            const label = level === 'error' ? 'Needs attention' : level === 'warning' ? 'Warning' : 'Update';
            const tone = level === 'error' ? 'is-error' : level === 'warning' ? 'is-warning' : '';
            const message = event.message.replace(/^\[[^\]]+\]\s*/, '');
            return `<li class="overview-activity-item">
                <span class="overview-activity-mark ${tone}" aria-hidden="true"></span>
                <div class="overview-activity-copy">
                    <a href="/agents/${encodeURIComponent(event.name)}">${escape(event.name)}</a>
                    <p>${escape(message)}</p>
                </div>
                <span class="overview-activity-type">${escape(label)}</span>
                <time>${escape(relativeTime(event.timestamp))}</time>
            </li>`;
        }).join('') : '<li class="overview-activity-empty">No agent activity yet. Updates will appear here when an agent runs.</li>';
    }

    async function refresh() {
        const response = await fetch('/api/status', { headers: { Accept: 'application/json' } });
        if (!response.ok) throw new Error('Runtime status could not be loaded.');
        const payload = await response.json();
        const agents = Object.values(payload.agents || {});
        const running = agents.filter((agent) => agent.status === 'Running').length;
        const waiting = agents.filter((agent) => waitingStates.includes(agent.status)).length;
        document.getElementById('overview-total').textContent = agents.length;
        document.getElementById('overview-running').textContent = running;
        document.getElementById('overview-waiting').textContent = waiting;
        const state = document.getElementById('overview-workspace-state');
        state.textContent = running ? 'Operational' : waiting ? 'Attention needed' : 'All quiet';
        state.className = 'overview-workspace-status ' + (running ? 'is-running' : waiting ? 'is-waiting' : 'is-idle');
        renderActivity(payload.agents || {});
        document.getElementById('overview-updated').textContent = 'Updated ' + new Date().toLocaleTimeString();
        document.getElementById('overview-error').hidden = true;
    }

    function showError(error) {
        const node = document.getElementById('overview-error');
        node.hidden = false;
        node.textContent = error.message || 'Runtime status unavailable.';
        activityList.innerHTML = '<li class="overview-activity-empty">Activity is unavailable while the runtime is disconnected.</li>';
    }
    refresh().catch(showError);
    window.setInterval(() => refresh().catch(() => {}), 5000);
})();
