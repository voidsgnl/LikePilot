(() => {
    const body = document.getElementById('agent-directory-body');
    if (!body) return;
    const search = document.getElementById('agent-search');
    const filter = document.getElementById('agent-status-filter');
    let entries = [];
    const escape = (value) => String(value ?? '—').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const statusClass = (status) => 'status-' + String(status || 'unknown').toLowerCase().replace(/[^a-z0-9]+/g, '-');
    function render() {
        const term = (search.value || '').trim().toLowerCase();
        const selected = filter.value;
        const rows = entries.filter(([name, agent]) => {
            const matchesTerm = !term || [name, agent.site, agent.platform].some((v) => String(v || '').toLowerCase().includes(term));
            const isWaiting = ['Awaiting Login', 'Login Success', 'Awaiting Switch'].includes(agent.status);
            const matchesStatus = selected === 'all' || (selected === 'waiting' ? isWaiting : agent.status === selected);
            return matchesTerm && matchesStatus;
        });
        const emptyMessage = entries.length === 0
            ? 'No agents configured. Create an agent to get started.'
            : 'No agents match these filters.';
        body.innerHTML = rows.length ? rows.map(([name, agent]) => `
            <tr>
                <td><a class="directory-agent-link" href="/agents/${encodeURIComponent(name)}">${escape(name)}</a><div class="section-subtle mono">${escape(agent.chrome_profile || 'No browser profile')}</div></td>
                <td><span class="status-badge ${statusClass(agent.status)}">${escape(agent.status)}</span></td>
                <td>${escape(agent.site)}</td><td>${escape(agent.platform)}</td>
                <td class="mono">${escape(agent.credits)}</td>
                <td><a class="btn-secondary btn-compact" href="/agents/${encodeURIComponent(name)}">Open ↗</a></td>
            </tr>`).join('') : `<tr><td colspan="6" class="section-subtle">${emptyMessage}</td></tr>`;
    }
    async function refresh() {
        const response = await fetch('/api/status', {headers:{Accept:'application/json'}});
        if (!response.ok) throw new Error('Agent inventory is unavailable.');
        const data = await response.json();
        entries = Object.entries(data.agents || {});
        document.getElementById('directory-updated').textContent = 'Updated ' + new Date().toLocaleTimeString();
        render();
    }
    search.addEventListener('input', render);
    filter.addEventListener('change', render);
    refresh().catch((error) => { body.innerHTML = '<tr><td colspan="6" class="section-subtle">' + escape(error.message) + '</td></tr>'; });
    window.setInterval(() => refresh().catch(() => {}), 5000);
})();