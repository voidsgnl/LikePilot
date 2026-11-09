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
            root.querySelectorAll('[data-agent-action]').forEach((button) => { button.hidden = true; });
            byId('agent-platform-select').hidden = true;
            byId('agent-confirm-platform').hidden = true;
            byId('agent-event-list').innerHTML = '<div class="empty-state">No runtime events available.</div>';
            return;
        }
        set('agent-name', name);
        const summary = [agent.site, agent.platform].filter(Boolean).join(' · ') || 'Agent runtime';
        set('agent-summary', agent.status === 'Awaiting Social Login'
            ? summary + ' · Sign in to the social platform in the open browser window. The current task will resume automatically.'
            : summary);
        const badge = byId('agent-status');
        badge.textContent = agent.status || 'Unknown';
        badge.className = 'status-badge status-' + String(agent.status || 'unknown').toLowerCase().replace(/[^a-z0-9]+/g, '-');
        set('agent-credits', agent.credits);
        set('agent-gain', (Number(agent.session_gain) >= 0 ? '+' : '') + Number(agent.session_gain || 0));
        set('agent-provider', agent.site);
        set('agent-platform', agent.platform);
        set('agent-profile', agent.chrome_profile || agent.browser_profile);
        set('agent-proxy', agent.proxy || 'Not configured');
        set('agent-fallback', agent.fallback_chain || agent.fallback_platform || 'None');
        set('agent-heartbeat', agent.heartbeat_at);
        set('agent-session-start', agent.session_started_at);
        const events = byId('agent-event-list');
        const logs = Array.isArray(agent.logs) ? agent.logs : [];
        events.innerHTML = logs.length ? logs.map((item) => {
            const line = String(item);
            const splitAt = line.lastIndexOf(' [');
            const closeAt = line.indexOf('] ', splitAt);
            const timestamp = splitAt >= 0 ? line.slice(0, splitAt) : '';
            const level = splitAt >= 0 && closeAt > splitAt ? line.slice(splitAt + 2, closeAt) : 'INFO';
            const message = closeAt >= 0 ? line.slice(closeAt + 2) : line;
            return '<article class="event-row"><div class="event-row-meta"><span class="event-level">' +
                safe(level) + '</span><time>' + safe(timestamp) +
                '</time></div><p>' + safe(message) + '</p></article>';
        }).join('') : '<div class="empty-state">No recent events for this agent.</div>';
        const actionAvailability = {
            start: agent.status === 'Stopped',
            ready: agent.status === 'Awaiting Login',
            initialize: agent.status === 'Login Success',
            pause: agent.status === 'Running' || agent.status === 'Awaiting Social Login',
            resume: agent.status === 'Paused',
            restart: agent.status !== 'Stopped',
            stop: agent.status !== 'Stopped'
        };
        root.querySelectorAll('[data-agent-action]').forEach((button) => {
            const available = Boolean(actionAvailability[button.dataset.agentAction]);
            button.hidden = !available;
            button.disabled = !available;
        });
        const platformSelect = byId('agent-platform-select');
        if (platformSelect) {
            const supported = Array.isArray(agent.supported_platforms) ? agent.supported_platforms : [];
            platformSelect.replaceChildren(...supported.map((platform) => {
                const option = document.createElement('option');
                option.value = platform;
                option.textContent = platform;
                return option;
            }));
            if (supported.includes(agent.platform)) platformSelect.value = agent.platform;
        }
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

    byId('agent-confirm-platform')?.addEventListener('click', async (event) => {
        const button = event.currentTarget;
        const platform = byId('agent-platform-select')?.value;
        button.disabled = true;
        try {
            const response = await fetch('/api/platform', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, platform })
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.message || 'Platform update failed.');
            window.showNotification?.(result.message || 'Platform updated.', 'success');
            await loadAgent();
        } catch (error) {
            window.showNotification?.(error.message, 'error');
        } finally {
            button.disabled = false;
        }
    });

    loadAgent().catch((error) => {
        set('agent-summary', error.message);
        window.showNotification?.(error.message, 'error');
    });
   
        window.setInterval(() => loadAgent().catch(() => {}), 5000);

    /* ========================================================================
       ORBIT · runtime mirror
       Reads the hidden carriers #agent-heartbeat / #agent-session-start
       (written by loadAgent above) and mirrors them into the Pulse UI.
       Decorates .event-row with .is-warn / .is-error for the timeline dots.
       Zero interference with the existing 5s data poll.
       ======================================================================== */
    (function mirrorRuntime() {
        const heartbeatHidden = document.getElementById('agent-heartbeat');
        const sessionHidden   = document.getElementById('agent-session-start');
        const eventsHost      = document.getElementById('agent-event-list');
        if (!heartbeatHidden || !eventsHost) return;

        const heartbeatUtc = document.getElementById('agent-heartbeat-utc');
        const heartbeatRel = document.getElementById('agent-heartbeat-rel');
        const sessionUtc   = document.getElementById('agent-session-start-utc');
        const sessionRel   = document.getElementById('agent-session-start-rel');
        const uptimeEl     = document.getElementById('agent-uptime');
        const pulseEl      = document.getElementById('agent-pulse');
        const chipEl       = document.getElementById('agent-runtime-chip');

        function parseIso(str) {
            if (!str || str === '—') return null;
            const t = Date.parse(str);
            return Number.isNaN(t) ? null : t;
        }

        function pad(n) { return String(n).padStart(2, '0'); }

        function fmtAbsolute(ms) {
            if (!ms) return '—';
            const d = new Date(ms);
            return `${d.getUTCFullYear()}-${pad(d.getUTCMonth()+1)}-${pad(d.getUTCDate())} `
                 + `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())} UTC`;
        }

        function fmtRelative(ms) {
            if (!ms) return '—';
            const s = Math.max(0, Math.floor((Date.now() - ms) / 1000));
            if (s < 5)    return 'just now';
            if (s < 60)   return `${s}s ago`;
            if (s < 3600) return `${Math.floor(s/60)}m ${s%60}s ago`;
            if (s < 86400)return `${Math.floor(s/3600)}h ago`;
            return `${Math.floor(s/86400)}d ago`;
        }

        function fmtDuration(ms) {
            if (!ms) return '—';
            const s = Math.floor(ms / 1000);
            const h = Math.floor(s / 3600);
            const m = Math.floor((s % 3600) / 60);
            const sec = s % 60;
            if (h > 0) return `${h}h ${m}m`;
            if (m > 0) return `${m}m ${sec}s`;
            return `${sec}s`;
        }

        function refreshPulseState() {
            const hb = parseIso(heartbeatHidden.textContent);
            if (!hb) {
                pulseEl?.classList.remove('is-stale', 'is-dead');
                pulseEl?.classList.add('is-stale');
                chipEl?.classList.remove('is-live', 'is-warn');
                chipEl?.classList.add('is-idle');
                if (chipEl) chipEl.textContent = 'No heartbeat';
                if (heartbeatUtc) heartbeatUtc.textContent = '—';
                if (heartbeatRel) {
                    heartbeatRel.textContent = '—';
                    heartbeatRel.classList.remove('is-stale', 'is-dead');
                }
                return;
            }
            const age = Date.now() - hb;
            pulseEl?.classList.remove('is-stale', 'is-dead');
            chipEl?.classList.remove('is-live', 'is-warn', 'is-idle');

            if (age > 60_000) {
                pulseEl?.classList.add('is-dead');
                chipEl?.classList.add('is-warn');
                if (chipEl) chipEl.textContent = 'Stale';
            } else if (age > 15_000) {
                pulseEl?.classList.add('is-stale');
                chipEl?.classList.add('is-warn');
                if (chipEl) chipEl.textContent = 'Idle';
            } else {
                chipEl?.classList.add('is-live');
                if (chipEl) chipEl.textContent = 'Live';
            }

            if (heartbeatUtc) heartbeatUtc.textContent = fmtAbsolute(hb);
            if (heartbeatRel) {
                heartbeatRel.textContent = fmtRelative(hb);
                heartbeatRel.classList.toggle('is-stale', age > 15_000 && age <= 60_000);
                heartbeatRel.classList.toggle('is-dead',  age > 60_000);
            }
        }

        function refreshSessionState() {
            const start = parseIso(sessionHidden?.textContent);
            if (sessionUtc) sessionUtc.textContent = start ? fmtAbsolute(start) : '—';
            if (sessionRel) sessionRel.textContent = start ? fmtRelative(start) : '—';
            if (uptimeEl)   uptimeEl.textContent   = start ? fmtDuration(Date.now() - start) : '—';
        }

        function decorateEventRows() {
            eventsHost.querySelectorAll('.event-row').forEach((row) => {
                const levelEl = row.querySelector('.event-level');
                if (!levelEl) return;
                const level = (levelEl.textContent || '').toUpperCase();
                row.classList.toggle('is-warn',  level.includes('WARN'));
                row.classList.toggle('is-error', level.includes('ERROR') || level.includes('CRIT'));
            });
        }

        /* 1s ticker — drives relative times + uptime + pulse state */
        setInterval(() => {
            refreshPulseState();
            refreshSessionState();
        }, 1000);

        /* re-decorate whenever agent-detail.js rewrites the event list */
        const observer = new MutationObserver(decorateEventRows);
        observer.observe(eventsHost, { childList: true, subtree: true });

        /* also react when the hidden carriers get new text */
        const hbObserver = new MutationObserver(() => {
            refreshPulseState();
            decorateEventRows();
        });
        if (heartbeatHidden) hbObserver.observe(heartbeatHidden, { childList: true, characterData: true, subtree: true });
        if (sessionHidden)   hbObserver.observe(sessionHidden,   { childList: true, characterData: true, subtree: true });

        /* first paint */
        refreshPulseState();
        refreshSessionState();
        decorateEventRows();
    })();
})();