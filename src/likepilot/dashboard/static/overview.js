(() => {
    const body = document.getElementById('overview-agent-rows');
    if (!body) return;
    const escape = (value) => String(value ?? '—').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const statusClass = (status) => 'status-' + String(status || 'unknown').toLowerCase().replace(/[^a-z0-9]+/g, '-');
    async function refresh() {
        const response = await fetch('/api/status', {headers:{Accept:'application/json'}});
        if (!response.ok) throw new Error('Runtime status could not be loaded.');
        const payload = await response.json();
        const entries = Object.entries(payload.agents || {});
        const values = entries.map(([,agent]) => agent);
        const waiting = values.filter((agent) => ['Awaiting Login','Login Success','Awaiting Switch'].includes(agent.status)).length;
        document.getElementById('overview-total').textContent = values.length;
        document.getElementById('overview-running').textContent = values.filter((agent) => agent.status === 'Running').length;
        document.getElementById('overview-waiting').textContent = waiting;
        document.getElementById('overview-stopped').textContent = values.filter((agent) => agent.status === 'Stopped').length;
        body.innerHTML = entries.length ? entries.slice(0,8).map(([name,agent]) => `<tr><td><a class="directory-agent-link" href="/agents/${encodeURIComponent(name)}">${escape(name)}</a></td><td><span class="status-badge ${statusClass(agent.status)}">${escape(agent.status)}</span></td><td>${escape(agent.site)}</td><td>${escape(agent.platform)}</td><td class="mono">${escape(agent.credits)}</td></tr>`).join('') : '<tr><td colspan="5" class="section-subtle">No agents configured. Create one to populate the runtime.</td></tr>';
        document.getElementById('overview-updated').textContent = 'Last updated ' + new Date().toLocaleTimeString();
        document.getElementById('overview-error').hidden = true;
    }
    refresh().catch((error) => { const node=document.getElementById('overview-error');node.hidden=false;node.textContent=error.message;body.innerHTML='<tr><td colspan="5" class="section-subtle">Runtime status unavailable.</td></tr>'; });
    window.setInterval(() => refresh().catch(() => {}), 5000);
})();