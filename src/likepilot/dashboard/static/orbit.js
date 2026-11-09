/* ============================================================================
   ORBIT — behaviour.
   - Reads the current page from <body data-page="...">.
   - Renders 5 nav slots on the orbit pointing at real Flask routes.
   - Rotates the ring so the active slot is at 12 o'clock.
   - Handles the dark/light theme switch.
   - Keeps the core alive (credits from /api/status, if available).
   - ← → keyboard shortcuts navigate between slots.
   - Preserves all existing dashboard.js behaviour (notifications, modal, etc.)
   ============================================================================ */

(function () {
    'use strict';

    /* -------- the 5 slots, mapped to real Flask routes -------- */
    const SLOTS = [
        { id: 'dashboard', label: 'Overview',  icon: '◉', href: '/dashboard' },
        { id: 'analytics', label: 'Analytics', icon: '◈', href: '/analytics' },
        { id: 'agents',    label: 'Agents',    icon: '⬢', href: '/agents' },
        { id: 'settings',  label: 'Settings',  icon: '⚙', href: '/settings/browser' },
        { id: 'activity',  label: 'Activity',  icon: '✦', href: '/operations/logs' },
    ];

    /* Which slot is considered "active" for each Flask page. */
    const PAGE_TO_SLOT = {
        dashboard: 'dashboard',
        analytics: 'analytics',
        agents:    'agents',
        agent_detail: 'agents',
        settings:  'settings',
        providers: 'settings',
        platforms: 'settings',
        operations:'activity',
    };

    const root      = document.documentElement;
    const ring      = document.getElementById('orbit-ring');
    const body      = document.body;
    const pageKey   = (body && body.dataset.page) || 'dashboard';
    const activeId  = PAGE_TO_SLOT[pageKey] || 'dashboard';

    /* ============================================================
       THEME
       ============================================================ */
    const btnDark  = document.getElementById('orbit-theme-dark');
    const btnLight = document.getElementById('orbit-theme-light');

    function applyTheme(theme) {
        const next = theme === 'light' ? 'light' : 'dark';
        root.setAttribute('data-theme', next);
        try { localStorage.setItem('theme', next); } catch (_) {}
        if (btnDark)  { btnDark.classList.toggle('active', next === 'dark');  btnDark.setAttribute('aria-pressed',  String(next === 'dark')); }
        if (btnLight) { btnLight.classList.toggle('active', next === 'light'); btnLight.setAttribute('aria-pressed', String(next === 'light')); }
        const meta = document.querySelector('meta[name="theme-color"]');
        if (meta) meta.setAttribute('content', next === 'dark' ? '#070a12' : '#f4f6fb');
    }

    if (btnDark)  btnDark.addEventListener('click',  () => applyTheme('dark'));
    if (btnLight) btnLight.addEventListener('click', () => applyTheme('light'));

    /* Restore saved theme, default dark. */
    try {
        const saved = localStorage.getItem('theme');
        applyTheme(saved === 'light' ? 'light' : 'dark');
    } catch (_) { applyTheme('dark'); }

    /* ============================================================
       ORBIT RING
       ============================================================ */
    let currentIndex = Math.max(0, SLOTS.findIndex(s => s.id === activeId));
    let orbitRotation = 0;
    let resizeTimer = null;

    function computeRadius() {
        if (!ring) return 300;
        const rect = ring.getBoundingClientRect();
        return Math.max(120, rect.width / 2);
    }

    function buildSlots() {
        if (!ring) return;
        ring.innerHTML = '';
        const n = SLOTS.length;
        const radius = computeRadius();

        SLOTS.forEach((slot, i) => {
            const wrap = document.createElement('div');
            wrap.className = 'orbit-slot';

            const a = document.createElement('a');
            a.className = 'orbit-slot-btn';
            a.href = slot.href;
            a.setAttribute('aria-label', slot.label);
            a.dataset.slot = slot.id;

            const angle = (i / n) * 360;
            a.style.setProperty('--angle', `${angle}deg`);
            a.style.setProperty('--radius', `${radius}px`);
            a.style.setProperty('--orbit-rotation', `${orbitRotation}deg`);

            a.innerHTML = `<span class="orbit-slot-icon">${slot.icon}</span>` +
                          `<span class="orbit-slot-label">${slot.label}</span>`;

            /* Only intercept click for visual rotation when the target
               is the current page; otherwise let the browser navigate. */
            a.addEventListener('click', (e) => {
                if (slot.id === activeId) {
                    e.preventDefault();
                    currentIndex = i;
                    rotateTo(i);
                    updateActive();
                }
            });

            wrap.appendChild(a);
            ring.appendChild(wrap);
        });

        updateActive();
    }

    function rotateTo(index) {
        if (!ring) return;
        const n = SLOTS.length;
        const anglePerStep = 360 / n;
        orbitRotation = -index * anglePerStep;
        ring.style.transform = `rotate(${orbitRotation}deg)`;

        ring.querySelectorAll('.orbit-slot-btn').forEach(btn => {
            btn.style.setProperty('--orbit-rotation', `${orbitRotation}deg`);
        });
    }

    function updateActive() {
        if (!ring) return;
        ring.querySelectorAll('.orbit-slot-btn').forEach((btn) => {
            btn.classList.toggle('active', btn.dataset.slot === activeId);
        });
    }

    function bootOrbit() {
        buildSlots();
        rotateTo(currentIndex);
        const label = document.getElementById('orbit-hint-label');
        if (label) {
            const slot = SLOTS[currentIndex];
            if (slot) label.textContent = slot.label;
        }
    }

    /* rebuild on resize so radius stays correct */
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            buildSlots();
            rotateTo(currentIndex);
        }, 160);
    });

    /* ← → keyboard: navigate to sibling slot on the orbit */
    document.addEventListener('keydown', (e) => {
        const tag = (e.target && e.target.tagName) || '';
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
        if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
        e.preventDefault();
        const delta = e.key === 'ArrowRight' ? 1 : -1;
        const nextIndex = (currentIndex + delta + SLOTS.length) % SLOTS.length;
        window.location.href = SLOTS[nextIndex].href;
    });

    /* ============================================================
       THE CORE — pull live credits from /api/status (best-effort)
       ============================================================ */
    const coreValueEl  = document.getElementById('orbit-core-value');
    const coreLabelEl  = document.getElementById('orbit-core-label');
    const coreStatusEl = document.getElementById('orbit-core-status');
    const coreDeltaEl  = document.getElementById('orbit-core-delta');
    const coreEyebrowEl= document.getElementById('orbit-core-eyebrow');
    const coreStatusTxt= document.getElementById('orbit-core-status-label');

    function setCoreStatus(text, tone) {
        if (!coreStatusEl || !coreStatusTxt) return;
        coreStatusTxt.textContent = text;
        coreStatusEl.classList.remove('is-warn', 'is-idle');
        if (tone === 'warn') coreStatusEl.classList.add('is-warn');
        if (tone === 'idle') coreStatusEl.classList.add('is-idle');
    }

    function refreshCore() {
        if (typeof fetch !== 'function') return;
        fetch('/api/status', { headers: { Accept: 'application/json' } })
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (!data || !data.agents) {
                    setCoreStatus('Offline', 'warn');
                    return;
                }
                const entries = Object.values(data.agents);
                if (!entries.length) {
                    setCoreStatus('No agents', 'idle');
                    if (coreValueEl) coreValueEl.textContent = '0';
                    if (coreLabelEl) coreLabelEl.textContent = 'agents';
                    if (coreDeltaEl) { coreDeltaEl.textContent = 'Create your first agent'; coreDeltaEl.classList.add('is-warn'); }
                    return;
                }
                let totalCredits = 0;
                let totalGain = 0;
                let running = 0;
                let waiting = 0;
                entries.forEach(a => {
                    totalCredits += Number(a.credits || 0);
                    totalGain    += Number(a.session_gain || 0);
                    if (a.status === 'Running') running++;
                    if (['Awaiting Login','Login Success','Awaiting Social Login','Awaiting Switch','Paused'].includes(a.status)) waiting++;
                });
                if (coreValueEl) coreValueEl.textContent = totalCredits.toLocaleString();
                if (coreLabelEl) coreLabelEl.textContent = 'credits';
                if (coreEyebrowEl) coreEyebrowEl.textContent = entries.length + (entries.length === 1 ? ' agent' : ' agents');

                if (running)      setCoreStatus('Running',  'live');
                else if (waiting) setCoreStatus('Attention', 'warn');
                else              setCoreStatus('Idle',      'idle');

                if (coreDeltaEl) {
                    coreDeltaEl.classList.remove('is-warn');
                    if (totalGain >= 0) {
                        coreDeltaEl.textContent = `▲ +${totalGain.toLocaleString()} this session`;
                    } else {
                        coreDeltaEl.textContent = `▼ ${totalGain.toLocaleString()} this session`;
                        coreDeltaEl.classList.add('is-warn');
                    }
                }
            })
            .catch(() => setCoreStatus('Offline', 'warn'));
    }

    /* ============================================================
       LIVE PILL (kept compatible with dashboard.js)
       ============================================================ */
    /* dashboard.js already drives #live-updates-pill via setLiveIndicator().
       We don't touch it here; its class names are preserved in layout.html. */

    /* ============================================================
       BOOT
       ============================================================ */
    function boot() {
        bootOrbit();
        refreshCore();
        window.setInterval(refreshCore, 8000);
    }

    if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(boot);
    } else {
        boot();
    }
})();