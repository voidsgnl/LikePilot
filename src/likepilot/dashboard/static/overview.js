(() => {
    const body = document.getElementById('overview-agent-rows');
    if (!body) return;
    const escape = (value) => String(value ?? '—').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const statusClass = (status) => 'status-' + String(status || 'unknown').toLowerCase().replace(/[^a-z0-9]+/g, '-');
    let creditChart = null;
    let platformChart = null;
    const chartColors = ['#079cf0','#42bd70','#9875ed','#e46c86','#e4b34e','#39c4c7'];
    function renderCharts(data) {
        const styles = getComputedStyle(document.documentElement);
        const textColor = styles.getPropertyValue('--text-muted').trim() || '#a8b7cc';
        const gridColor = 'rgba(145,166,197,.13)';
        const history = data.history || [];
        const labels = history.map(item => item.time);
        const values = history.map(item => item.credits);
        const canvas = document.getElementById('overview-credit-chart');
        const empty = document.getElementById('overview-chart-empty');
        empty.hidden = values.length > 0;
        canvas.hidden = values.length === 0;
        if (creditChart) creditChart.destroy();
        if (values.length) {
            creditChart = new Chart(canvas, {
                type: 'line',
                data: {labels, datasets: [{data: values, borderColor:'#079cf0',backgroundColor:'rgba(7,156,240,.18)',fill:true,tension:.38,borderWidth:3,pointRadius:0,pointHoverRadius:5}]},
                options: {responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},interaction:{intersect:false,mode:'index'},scales:{x:{ticks:{color:textColor,maxTicksLimit:8,maxRotation:0},grid:{display:false}},y:{beginAtZero:true,ticks:{color:textColor},grid:{color:gridColor}}}}
            });
        }
        const platformEntries = Object.entries(data.platform_stats || {}).filter(([,count]) => Number(count) > 0);
        const total = platformEntries.reduce((sum,[,count]) => sum + Number(count),0);
        document.getElementById('overview-platform-total').textContent = total;
        const platformCanvas = document.getElementById('overview-platform-chart');
        if (platformChart) platformChart.destroy();
        if (platformEntries.length) {
            platformChart = new Chart(platformCanvas, {
                type:'doughnut',
                data:{labels:platformEntries.map(([name])=>name),datasets:[{data:platformEntries.map(([,count])=>count),backgroundColor:platformEntries.map((_,index)=>chartColors[index%chartColors.length]),borderWidth:0,hoverOffset:4}]},
                options:{responsive:true,maintainAspectRatio:false,cutout:'72%',plugins:{legend:{display:false},tooltip:{callbacks:{label:context=>`${context.label}: ${context.parsed}`}}}}
            });
            document.getElementById('overview-platform-legend').innerHTML = platformEntries.map(([name,count],index)=>`<div class="overview-legend-item"><i style="--legend-color:${chartColors[index%chartColors.length]}"></i><span>${escape(name)}</span><strong>${Number(count)}</strong></div>`).join('');
        } else {
            document.getElementById('overview-platform-legend').innerHTML = '<span class="section-subtle">No platform activity recorded.</span>';
        }
        const metrics = data.metrics || {};
        document.getElementById('overview-latest-credits').textContent = metrics.samples ? (metrics.latest_credits ?? '—') : '—';
        const gain = Number(metrics.session_gain || 0);
        document.getElementById('overview-session-gain').textContent = metrics.samples ? (gain > 0 ? '+' : '') + gain : '—';
    }
    async function refresh() {
        const response = await fetch('/api/status', {headers:{Accept:'application/json'}});
        if (!response.ok) throw new Error('Runtime status could not be loaded.');
        const payload = await response.json();
        const entries = Object.entries(payload.agents || {});
        const values = entries.map(([,agent]) => agent);
        const running = values.filter((agent) => agent.status === 'Running').length;
        const waiting = values.filter((agent) => ['Awaiting Login','Login Success','Awaiting Switch'].includes(agent.status)).length;
        const stopped = values.filter((agent) => agent.status === 'Stopped').length;
        document.getElementById('overview-total').textContent = values.length;
        document.getElementById('overview-running').textContent = running;
        document.getElementById('overview-waiting').textContent = waiting;
        document.getElementById('overview-stopped').textContent = stopped;
        const state = document.getElementById('overview-workspace-state');
        const detail = document.getElementById('overview-workspace-detail');
        state.textContent = running ? 'Operational' : 'Idle';
        detail.textContent = running ? `${running} active agent${running===1?'':'s'}` : 'No agents currently running';
        body.innerHTML = entries.length ? entries.slice(0,8).map(([name,agent]) => `<tr><td><a class="directory-agent-link" href="/agents/${encodeURIComponent(name)}">${escape(name)}</a></td><td><span class="status-badge ${statusClass(agent.status)}">${escape(agent.status)}</span></td><td>${escape(agent.site)}</td><td>${escape(agent.platform)}</td><td class="mono">${escape(agent.credits)}</td></tr>`).join('') : '<tr><td colspan="5" class="section-subtle">No agents configured. Create one to populate the runtime.</td></tr>';
        document.getElementById('overview-updated').textContent = new Date().toLocaleTimeString();
        document.getElementById('overview-error').hidden = true;
    }
    async function refreshStats() {
        try {
            const response = await fetch('/api/stats', {headers:{Accept:'application/json'}});
            if (!response.ok) throw new Error('Analytics unavailable');
            renderCharts(await response.json());
        } catch (_) {
            document.getElementById('overview-chart-empty').hidden = false;
            document.getElementById('overview-chart-empty').textContent = 'Credit activity is currently unavailable.';
        }
    }
    refresh().catch((error) => { const node=document.getElementById('overview-error');node.hidden=false;node.textContent=error.message;body.innerHTML='<tr><td colspan="5" class="section-subtle">Runtime status unavailable.</td></tr>'; });
    refreshStats();
    window.setInterval(() => refresh().catch(() => {}), 5000);
    window.setInterval(refreshStats, 30000);
})();
