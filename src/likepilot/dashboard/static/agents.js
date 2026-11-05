(function () {
    let focusedAgentName = new URLSearchParams(window.location.search).get('agent') || localStorage.getItem('focusedAgentName') || null;
    let searchTerm = '';
    let statusFilter = 'all';

    const PLATFORMS = [
        'Twitter',
        'Twitter Likes',
        'Twitter Retweets',
        'Instagram',
        'Instagram Likes',
        'IG Comments',
        'TikTok',
        'TikTok Likes',
        'YouTube Subs',
        'YouTube Likes',
        'Facebook Subs',
        'Facebook Likes',
        'FB Comments'
    ];

    // Enhanced search and filter functionality
    function initializeSearchAndFilters() {
        const searchInput = document.createElement('input');
        searchInput.type = 'text';
        searchInput.placeholder = 'Search agents...';
        searchInput.className = 'search-input';
        searchInput.style.cssText = `
            padding: 8px 12px;
            border-radius: 8px;
            border: 1px solid var(--border);
            background: var(--surface-muted);
            color: var(--text);
            font-size: 0.8rem;
            margin-bottom: 12px;
            width: 100%;
            max-width: 300px;
            backdrop-filter: blur(5px);
            transition: all 0.3s ease;
        `;

        searchInput.addEventListener('input', (e) => {
            searchTerm = e.target.value.toLowerCase();
            filterAgents();
        });

        const filterSelect = document.createElement('select');
        filterSelect.className = 'filter-select';
        filterSelect.style.cssText = `
            padding: 8px 12px;
            border-radius: 8px;
            border: 1px solid var(--border);
            background: var(--surface-muted);
            color: var(--text);
            font-size: 0.8rem;
            margin-bottom: 12px;
            margin-left: 12px;
            backdrop-filter: blur(5px);
            transition: all 0.3s ease;
        `;

        const options = [
            { value: 'all', label: 'All Status' },
            { value: 'running', label: 'Running' },
            { value: 'waiting', label: 'Waiting' },
            { value: 'stopped', label: 'Stopped' }
        ];

        options.forEach(option => {
            const opt = document.createElement('option');
            opt.value = option.value;
            opt.textContent = option.label;
            filterSelect.appendChild(opt);
        });

        filterSelect.addEventListener('change', (e) => {
            statusFilter = e.target.value;
            filterAgents();
        });

        const controlsContainer = document.createElement('div');
        controlsContainer.className = 'search-controls';
        controlsContainer.style.cssText = `
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        `;

        controlsContainer.appendChild(searchInput);
        controlsContainer.appendChild(filterSelect);

        const agentFeedback = document.getElementById('agent-feedback');
        if (agentFeedback && agentFeedback.parentNode) {
            agentFeedback.parentNode.insertBefore(controlsContainer, agentFeedback);
        }
    }

    function filterAgents() {
        const agentCards = document.querySelectorAll('.agent-card, [data-agent-name]');
        agentCards.forEach(card => {
            const agentName = card.getAttribute('data-agent-name') || card.textContent.toLowerCase();
            const agentStatus = card.getAttribute('data-agent-status') || 'unknown';

            const matchesSearch = !searchTerm || agentName.toLowerCase().includes(searchTerm);
            const matchesFilter = statusFilter === 'all' || agentStatus === statusFilter;

            if (matchesSearch && matchesFilter) {
                card.style.display = '';
                card.style.animation = 'slideIn 0.3s ease-out';
            } else {
                card.style.display = 'none';
            }
        });
    }

    async function controlAgent(name, action) {
        if (action === 'stop') {
            const confirmed = await showConfirmModal(`Stop ${name}? The current browser session will be closed.`, {
                title: 'Stop agent',
                confirmLabel: 'Stop',
                cancelLabel: 'Keep running',
                confirmClass: 'btn-danger'
            });
            if (!confirmed) {
                return;
            }
        }

        fetchJson('/api/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, action: action })
        }).then((response) => {
            const feedback = document.getElementById('agent-feedback');
            if (feedback && response && response.message) {
                feedback.innerHTML = `<span class="section-subtle">${escapeHtml(response.message)}</span>`;
            }
            updateStatus();
        }).catch(() => {
            setLoadingState(document.getElementById('agent-feedback'), 'Failed to send agent command.');
        });
    }

    function changePlatform(name) {
        const platform = document.getElementById(`platform-${name}`).value;
        fetchJson('/api/platform', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, platform: platform })
        }).then(() => {
            updateStatus();
        }).catch(() => {
            setLoadingState(document.getElementById('agent-feedback'), 'Failed to change platform.');
        });
    }

    function confirmSwitch(name) {
        changePlatform(name);
    }

    function toggleAutoSwitch() {
        fetchJson('/api/toggle_auto_switch', { method: 'POST' }).catch(() => {
            setLoadingState(document.getElementById('agent-feedback'), 'Failed to toggle auto rotation.');
        });
    }

    function statusChip(status) {
        if (status === 'Running') return 'chip chip-running status-running';
        if (status === 'Paused') return 'chip chip-paused status-paused';
        if (status === 'Awaiting Login' || status === 'Login Success' || status === 'Awaiting Switch') return 'chip chip-waiting';
        return 'chip chip-stopped';
    }

    function statusLabel(status) {
        if (status === 'Login Success') return 'Login Success';
        if (status === 'Awaiting Login') return 'Awaiting Login';
        return status;
    }

    function renderControls(name, status, switchPending) {
        let html = '';
        if (status === 'Stopped') {
            html += `<button class="btn-primary btn-compact" data-agent-action="start" data-agent-name="${escapeHtml(name)}">Start</button>`;
        }
        if (status === 'Awaiting Login') {
            html += `<button class="btn-secondary btn-compact" data-agent-action="ready" data-agent-name="${escapeHtml(name)}">Ready</button>`;
        }
        if (status === 'Login Success') {
            html += `<button class="btn-secondary btn-compact" data-agent-action="initialize" data-agent-name="${escapeHtml(name)}">Initialize</button>`;
            html += `<button class="btn-secondary btn-compact" data-agent-action="ready" data-agent-name="${escapeHtml(name)}">Ready</button>`;
        }
        if (status === 'Running') {
            html += `<button class="btn-warning btn-compact" data-agent-action="pause" data-agent-name="${escapeHtml(name)}">Pause</button>`;
        }
        if (status === 'Paused') {
            html += `<button class="btn-primary btn-compact" data-agent-action="resume" data-agent-name="${escapeHtml(name)}">Resume</button>`;
        }
        if (status === 'Awaiting Switch' || switchPending) {
            html += `<button class="btn-primary btn-compact" data-agent-action="confirm-switch" data-agent-name="${escapeHtml(name)}">Confirm</button>`;
        }
        if (status !== 'Stopped') {
            html += `<button class="btn-danger btn-compact" data-agent-action="stop" data-agent-name="${escapeHtml(name)}">Stop</button>`;
        }
        return html;
    }

    function platformOptions(selected) {
        return PLATFORMS.map((platform) => `
            <option value="${escapeHtml(platform)}" ${platform === selected ? 'selected' : ''}>${escapeHtml(platform)}</option>
        `).join('');
    }

    function createAgentCard(name, status) {
        const profileLabel = status.chrome_profile || 'No profile';
        return `
            <section class="panel focus-card" id="agent-card-${escapeHtml(name)}">
                <div class="focus-main stack-sm">
                    <div class="inline-row">
                        <div>
                            <div class="focus-title">${escapeHtml(name)}</div>
                            <div class="mono focus-meta">${escapeHtml(status.site || 'Like4Like')} | ${escapeHtml(profileLabel)}</div>
                        </div>
                        <div class="focus-header-actions">
                            <div id="status-${escapeHtml(name)}" class="${statusChip(status.status)}">${escapeHtml(statusLabel(status.status))}</div>
                            <div class="actions focus-inline-actions" id="controls-${escapeHtml(name)}"></div>
                            <a class="btn-secondary btn-compact" href="/agents/${encodeURIComponent(name)}">Open workspace ↗</a>
                        </div>
                    </div>

                    <div class="card-grid-3">
                        <div class="stat-card focus-stat">
                            <div class="stat-label">Current</div>
                            <div class="stat-value focus-stat-value" id="credits-${escapeHtml(name)}">0</div>
                        </div>
                        <div class="stat-card focus-stat">
                            <div class="stat-label">Session gain</div>
                            <div class="stat-value focus-stat-value focus-positive" id="gain-${escapeHtml(name)}">+0</div>
                        </div>
                        <div class="stat-card focus-stat">
                            <div class="stat-label">Peak</div>
                            <div class="stat-value focus-stat-value" id="peak-${escapeHtml(name)}">0</div>
                        </div>
                    </div>

                    ${status.switch_pending ? `
                        <div class="switch-notice">
                            <div class="section-subtle">${escapeHtml(status.switch_reason || `${status.platform} is exhausted. Choose the next platform.`)}</div>
                        </div>
                    ` : ''}

                    <div class="focus-advanced" id="advanced-${escapeHtml(name)}">
                        <div class="focus-controls">
                            <div>
                                <div class="section-subtle focus-label">Platform</div>
                                <select id="platform-${escapeHtml(name)}" data-platform-name="${escapeHtml(name)}" data-switch-pending="${status.switch_pending ? '1' : '0'}">
                                    ${platformOptions(status.platform)}
                                </select>
                            </div>
                            <div class="focus-profile-box">
                                <div class="section-subtle focus-label">${status.switch_pending ? 'Fallback' : 'Profile'}</div>
                                <div class="mono focus-meta-static">${escapeHtml(status.switch_pending ? (status.fallback_platform || 'Manual choice') : status.chrome_profile)}</div>
                            </div>
                        </div>
                    </div>
                </div>

                <aside class="focus-side stack-sm">
                    <div class="inline-row">
                        <div class="section-subtle focus-label">Recent events</div>
                        <div class="mono focus-meta">Latest 3</div>
                    </div>
                    <div id="logs-${escapeHtml(name)}" class="event-list event-list-compact"></div>
                </aside>
            </section>
        `;
    }

    function renderFocusNav(agentEntries) {
        const nav = document.getElementById('agent-focus-nav');
        if (!agentEntries.length) {
            nav.innerHTML = `<div class="section-subtle">No agents configured yet.</div>`;
            return;
        }

        nav.innerHTML = agentEntries.map(([name], index) => `
            <button
                type="button"
                class="btn-secondary btn-compact pager-button ${name === focusedAgentName ? 'active' : ''}"
                data-focus-agent="${escapeHtml(name)}"
                title="${escapeHtml(name)}"
            >
                <span class="pager-index">${index + 1}</span>
                <span class="pager-name">${escapeHtml(name)}</span>
            </button>
        `).join('');
    }

    function renderFocusCard(name, status) {
        const cardHost = document.getElementById('agent-focus-card');
        if (!name || !status) {
            cardHost.innerHTML = `<div class="section-subtle">Choose an agent.</div>`;
            cardHost.removeAttribute('data-render-key');
            return;
        }
        const renderKey = JSON.stringify({
            name: name,
            status: status.status,
            platform: status.platform,
            chrome_profile: status.chrome_profile,
            site: status.site,
            switch_pending: status.switch_pending,
            switch_reason: status.switch_reason,
            fallback_platform: status.fallback_platform
        });
        if (cardHost.getAttribute('data-render-key') === renderKey && document.getElementById(`agent-card-${name}`)) {
            return;
        }
        cardHost.innerHTML = createAgentCard(name, status);
        cardHost.setAttribute('data-render-key', renderKey);
    }

    function renderLiveTable(agentEntries) {
        const body = document.getElementById('agent-live-body');
        if (!agentEntries.length) {
            body.innerHTML = `<tr><td colspan="8" class="section-subtle">No agents configured yet.</td></tr>`;
            return;
        }

        body.innerHTML = agentEntries.map(([name, status]) => `
            <tr>
                <td><strong>${escapeHtml(name)}</strong></td>
                <td><span class="${statusChip(status.status)}">${escapeHtml(statusLabel(status.status))}</span></td>
                <td>${escapeHtml(status.site || 'Like4Like')}</td>
                <td>${escapeHtml(status.platform)}</td>
                <td>${status.credits}</td>
                <td>${formatSignedNumber(status.session_gain)}</td>
                <td>${status.session_peak}</td>
                <td>${escapeHtml(status.switch_pending ? (status.switch_reason || 'Manual switch needed') : (status.last_error || '-'))}</td>
            </tr>
        `).join('');
    }

    function renderRecentLogs(agentEntries) {
        const logsHost = document.getElementById('agent-logs-list');
        const items = agentEntries.flatMap(([name, status]) =>
            (status.logs || []).slice(-2).map((log) => ({ name, log }))
        ).slice(-8).reverse();

        logsHost.innerHTML = items.length
            ? items.map((item) => `
                <div class="event-item">
                    <div style="font-weight:800; margin-bottom:6px;">${escapeHtml(item.name)}</div>
                    <div class="mono" style="font-size:0.76rem; color:var(--text-muted); line-height:1.5;">${escapeHtml(item.log)}</div>
                </div>
            `).join('')
            : `<div class="section-subtle">No recent logs yet.</div>`;
    }

    function renderStatus(data) {
        document.getElementById('auto-switch-toggle').checked = data.auto_switch;
        document.getElementById('auto-switch-state').innerText = data.auto_switch ? 'On' : 'Off';

        const feedback = document.getElementById('agent-feedback');
        const agentEntries = Object.entries(data.agents);
        let total = 0;
        let running = 0;
        let waiting = 0;

        if (!focusedAgentName || !data.agents[focusedAgentName]) {
            focusedAgentName = agentEntries.length ? agentEntries[0][0] : null;
        }

        renderFocusNav(agentEntries);
        renderFocusCard(focusedAgentName, focusedAgentName ? data.agents[focusedAgentName] : null);
        renderLiveTable(agentEntries);
        renderRecentLogs(agentEntries);

        const focusCard = document.getElementById(`agent-card-${focusedAgentName}`);
        if (focusCard) {
            const status = data.agents[focusedAgentName];
            const statusEl = document.getElementById(`status-${focusedAgentName}`);
            statusEl.className = statusChip(status.status);
            statusEl.innerText = statusLabel(status.status);

            document.getElementById(`credits-${focusedAgentName}`).innerText = status.credits;
            document.getElementById(`gain-${focusedAgentName}`).innerText = formatSignedNumber(status.session_gain);
            document.getElementById(`peak-${focusedAgentName}`).innerText = status.session_peak;

            const selectEl = document.getElementById(`platform-${focusedAgentName}`);
            if (document.activeElement !== selectEl) {
                selectEl.value = status.platform;
            }

            const controlsEl = document.getElementById(`controls-${focusedAgentName}`);
            const controlKey = `${status.status}:${status.switch_pending ? '1' : '0'}`;
            if (controlsEl.getAttribute('data-last-status') !== controlKey) {
                controlsEl.innerHTML = renderControls(focusedAgentName, status.status, status.switch_pending);
                controlsEl.setAttribute('data-last-status', controlKey);
            }

            const logsEl = document.getElementById(`logs-${focusedAgentName}`);
            const newLogs = status.logs.slice(-3).map(log => `
                <div class="event-item">
                    <div class="mono" style="font-size:0.76rem; color:var(--text-muted); line-height:1.5;">${escapeHtml(log)}</div>
                </div>
            `).join('');
            if (logsEl.innerHTML !== newLogs) {
                logsEl.innerHTML = newLogs || `<div class="section-subtle">No events yet.</div>`;
            }
        }

        for (const [, status] of agentEntries) {
            total++;
            if (status.status === 'Running') running++;
            if (status.status === 'Awaiting Login' || status.status === 'Login Success' || status.status === 'Awaiting Switch' || status.status === 'Paused') waiting++;
        }

        document.getElementById('agent-count').innerText = total;
        document.getElementById('running-count').innerText = running;
        document.getElementById('waiting-count').innerText = waiting;
        feedback.innerHTML = total
            ? `<span class="section-subtle">Showing ${total} configured agent${total === 1 ? '' : 's'}.</span>`
            : `<span class="section-subtle">No agents are configured yet. Add one from Configuration.</span>`;
    }

    function updateStatus() {
        fetchJson('/api/status')
            .then(renderStatus)
            .catch(() => {
                setLoadingState(document.getElementById('agent-feedback'), 'Unable to load agent status right now.');
            });
    }

    document.addEventListener('change', (event) => {
        if (event.target.matches('#auto-switch-toggle')) {
            toggleAutoSwitch();
            return;
        }
        if (event.target.matches('[data-platform-name]')) {
            if (event.target.getAttribute('data-switch-pending') === '1') {
                const feedback = document.getElementById('agent-feedback');
                if (feedback) {
                    feedback.innerHTML = `<span class="section-subtle">Platform selected. Click Confirm to switch.</span>`;
                }
                return;
            }
            changePlatform(event.target.getAttribute('data-platform-name'));
        }
    });

    document.addEventListener('click', (event) => {
        const focusButton = event.target.closest('[data-focus-agent]');
        if (focusButton) {
            focusedAgentName = focusButton.getAttribute('data-focus-agent');
            localStorage.setItem('focusedAgentName', focusedAgentName);
            updateStatus();
            return;
        }
        const button = event.target.closest('[data-agent-action]');
        if (!button) return;
        if (button.getAttribute('data-agent-action') === 'confirm-switch') {
            confirmSwitch(button.getAttribute('data-agent-name'));
            return;
        }
        void controlAgent(
            button.getAttribute('data-agent-name'),
            button.getAttribute('data-agent-action')
        );
    });

    window.toggleAutoSwitch = toggleAutoSwitch;

    // Initialize search and filter functionality
    initializeSearchAndFilters();

    createEventStream(
        '/api/stream/status',
        renderStatus,
        () => setLoadingState(document.getElementById('agent-feedback'), 'Live status stream unavailable. Falling back to polling.'),
        2000,
        updateStatus
    );
})();
