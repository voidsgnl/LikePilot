// Enhanced dashboard functionality with modern UI features
function showLoadingState(elementId, message = 'Loading...') {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <div class="loading-state" style="display: flex; align-items: center; justify-content: center; gap: 12px; padding: 20px;">
                <div class="loading-spinner" style="width: 20px; height: 20px; border: 2px solid var(--border); border-top: 2px solid var(--accent); border-radius: 50%; animation: spin 1s linear infinite;"></div>
                <span style="color: var(--text-muted); font-size: 0.8rem;">${message}</span>
            </div>
        `;
    }
}

function hideLoadingState(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        const loadingState = element.querySelector('.loading-state');
        if (loadingState) {
            loadingState.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => loadingState.remove(), 300);
        }
    }
}

function showNotification(message, type = 'info', duration = 3000) {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 16px;
        border-radius: 12px;
        background: var(--surface-strong);
        border: 1px solid var(--glass-border);
        backdrop-filter: blur(10px);
        box-shadow: var(--shadow-lg);
        color: var(--text);
        font-size: 0.85rem;
        z-index: 1000;
        animation: slideIn 0.3s ease-out;
        max-width: 300px;
    `;

    const colors = {
        success: 'var(--success)',
        error: 'var(--danger)',
        warning: 'var(--warning)',
        info: 'var(--accent)'
    };

    notification.style.borderLeft = `4px solid ${colors[type] || colors.info}`;
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;align-items:center;gap:8px;';
    const dot = document.createElement('span');
    dot.style.cssText = `width:8px;height:8px;border-radius:50%;background:${colors[type] || colors.info};flex-shrink:0;`;
    const label = document.createElement('span');
    label.textContent = String(message ?? '');
    row.append(dot, label);
    notification.appendChild(row);

    document.body.appendChild(notification);

    if (duration > 0) {
        setTimeout(() => {
            notification.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, duration);
    }

    return notification;
}

function updateSidebarButton(collapsed) {
    const collapseBtn = document.getElementById('sidebar-collapse-btn');
    const icon = collapseBtn?.querySelector('.collapse-icon');
    if (icon) {
        icon.innerText = collapsed ? '▸' : '◂';
        icon.style.transition = 'transform 0.3s ease';
    }
    if (collapseBtn) {
        const label = collapsed ? 'Expand navigation' : 'Collapse navigation';
        collapseBtn.title = label;
        collapseBtn.setAttribute('aria-label', label);
    }
}

function updateThemeLabel(theme) {
    const preview = document.getElementById('theme-preview');
    if (preview) {
        preview.className = `theme-preview theme-preview-${theme || 'dark'}`;
        preview.style.animation = 'scaleIn 0.3s ease-out';
    }
    const select = document.getElementById('theme-select');
    if (select) {
        select.value = theme;
    }
}

function applyTheme(theme, notify = true) {
    const root = document.documentElement;
    const next = theme || 'light';
    root.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    updateThemeLabel(next);

    // Add smooth transition
    root.style.transition = 'all 0.3s ease';
    setTimeout(() => root.style.transition = '', 300);

    window.dispatchEvent(new CustomEvent('themechange', { detail: { theme: next } }));
    if (notify) showNotification(`Theme changed to ${next}`, 'info', 1500);
}

function initializeTheme() {
    const storedTheme = localStorage.getItem('theme') || 'light';
    const savedTheme = ['dark', 'light', 'high-contrast'].includes(storedTheme) ? storedTheme : 'light';
    applyTheme(savedTheme, false);
}

// Enhanced sidebar toggle with smooth animation
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const appShell = document.getElementById('app-shell');
    if (sidebar) {
        sidebar.classList.toggle('collapsed');
        appShell?.classList.toggle('sidebar-collapsed');
        localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed') ? 'true' : 'false');
        updateSidebarButton(sidebar.classList.contains('collapsed'));
        // Trigger resize event for charts
        window.dispatchEvent(new Event('resize'));
    }
}

function applyDensity(density, notify = true) {
    const next = density === 'compact' ? 'compact' : 'comfortable';
    document.documentElement.setAttribute('data-density', next);
    localStorage.setItem('layoutDensity', next);
    const select = document.getElementById('density-select');
    if (select) select.value = next;
    if (notify) showNotification(`Layout density: ${next}`, 'info', 1500);
}

function initializeDensity() {
    const stored = localStorage.getItem('layoutDensity') || 'comfortable';
    applyDensity(stored, false);
    const select = document.getElementById('density-select');
    select?.addEventListener('change', event => applyDensity(event.target.value));
}

function initializeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const appShell = document.getElementById('app-shell');
    const collapseBtn = document.getElementById('sidebar-collapse-btn');
    const savedState = localStorage.getItem('sidebarCollapsed');
    const savedCollapsed = savedState === null ? false : savedState === 'true';
    
    if (savedCollapsed && sidebar) {
        sidebar.classList.add('collapsed');
        appShell?.classList.add('sidebar-collapsed');
    }
    updateSidebarButton(savedCollapsed);
    
    if (collapseBtn) {
        collapseBtn.addEventListener('click', toggleSidebar);
    }
}

async function fetchJson(url, options) {
    const response = await fetch(url, options);
    if (!response.ok) {
        let message = `Request failed: ${response.status}`;
        try {
            const payload = await response.json();
            if (payload && payload.message) {
                message = payload.message;
            }
        } catch (_error) {
            // Leave the fallback message when the response is not JSON.
        }
        throw new Error(message);
    }
    return response.json();
}

function escapeHtml(value) {
    return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

function formatSignedNumber(value) {
    const number = Number(value || 0);
    return `${number >= 0 ? '+' : ''}${number}`;
}

function setLoadingState(element, message) {
    if (element) {
        element.innerHTML = `<div class="section-subtle">${escapeHtml(message)}</div>`;
    }
}

function setLiveIndicator(state) {
    const pill = document.getElementById('live-updates-pill');
    const label = document.getElementById('live-updates-label');
    if (!pill || !label) {
        return;
    }
    pill.classList.remove('live-pill-active', 'live-pill-warning', 'live-pill-offline');
    if (state === 'active') {
        pill.classList.add('live-pill-active');
        label.innerText = 'Live';
    } else if (state === 'offline') {
        pill.classList.add('live-pill-offline');
        label.innerText = 'Offline';
    } else {
        pill.classList.add('live-pill-warning');
        label.innerText = 'Fallback';
    }
}

let activeModalResolver = null;

function closeAppModal(result) {
    const modal = document.getElementById('app-modal');
    if (!modal) {
        return;
    }
    modal.hidden = true;
    modal.setAttribute('aria-hidden', 'true');
    if (activeModalResolver) {
        const resolver = activeModalResolver;
        activeModalResolver = null;
        resolver(result);
    }
}

function openAppModal(options) {
    const modal = document.getElementById('app-modal');
    const title = document.getElementById('app-modal-title');
    const body = document.getElementById('app-modal-body');
    const cancelButton = document.getElementById('app-modal-cancel');
    const confirmButton = document.getElementById('app-modal-confirm');
    if (!modal || !title || !body || !cancelButton || !confirmButton) {
        return Promise.resolve(false);
    }

    title.innerText = options.title || 'Confirm';
    body.innerHTML = options.html || escapeHtml(options.message || '');
    cancelButton.innerText = options.cancelLabel || 'Cancel';
    cancelButton.hidden = Boolean(options.hideCancel);
    confirmButton.innerText = options.confirmLabel || 'OK';
    confirmButton.className = `${options.confirmClass || 'btn-primary'} btn-compact`;
    modal.hidden = false;
    modal.setAttribute('aria-hidden', 'false');
    confirmButton.focus();

    if (activeModalResolver) {
        activeModalResolver(false);
    }

    return new Promise((resolve) => {
        activeModalResolver = resolve;
    });
}

function showConfirmModal(message, options = {}) {
    return openAppModal({
        title: options.title || 'Confirm action',
        message: message,
        confirmLabel: options.confirmLabel || 'Confirm',
        cancelLabel: options.cancelLabel || 'Cancel',
        confirmClass: options.confirmClass || 'btn-danger'
    });
}

function showAlertModal(message, options = {}) {
    return openAppModal({
        title: options.title || 'Notice',
        message: message,
        confirmLabel: options.confirmLabel || 'OK',
        hideCancel: true,
        confirmClass: options.confirmClass || 'btn-primary'
    });
}

function showSuccessModal(message, options = {}) {
    return showAlertModal(message, {
        title: options.title || 'Done',
        confirmLabel: options.confirmLabel || 'OK',
        confirmClass: options.confirmClass || 'btn-primary'
    });
}

function quickStatusClass(status) {
    if (status === 'Running') return 'quick-dot running';
    if (status === 'Awaiting Login' || status === 'Login Success' || status === 'Awaiting Switch') return 'quick-dot waiting';
    return 'quick-dot stopped';
}

function parseLogTimestamp(logLine) {
    if (!logLine || typeof logLine !== 'string') {
        return null;
    }
    const match = logLine.match(/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)/);
    if (!match) {
        return null;
    }
    const timestamp = Date.parse(match[1]);
    return Number.isNaN(timestamp) ? null : timestamp;
}

function hasRecentActivity(agentStatus) {
    if (!agentStatus || agentStatus.status === 'Stopped') {
        return false;
    }
    const logs = agentStatus.logs || [];
    const latestTimestamp = parseLogTimestamp(logs[logs.length - 1]);
    if (!latestTimestamp) {
        return false;
    }
    return (Date.now() - latestTimestamp) <= 120000;
}

function renderAgentQuickSwitch(data) {
    const host = document.getElementById('agent-quick-switch');
    if (!host) {
        return;
    }
    const agentEntries = Object.entries((data && data.agents) || {});
    if (!agentEntries.length) {
        host.innerHTML = `<span class="section-subtle">No agents configured.</span>`;
        return;
    }
    const activeAgent = new URLSearchParams(window.location.search).get('agent') || localStorage.getItem('focusedAgentName') || '';
    host.innerHTML = agentEntries.map(([name]) => `
        <a
            href="/agents/${encodeURIComponent(name)}"
            class="quick-agent ${name === activeAgent ? 'active' : ''}"
            data-quick-agent="${escapeHtml(name)}"
            title="${escapeHtml(name)}"
        >
            <span class="${quickStatusClass(data.agents[name].status)}"></span>
            <span class="quick-agent-name">${escapeHtml(name)}</span>
            <span class="quick-pulse ${hasRecentActivity(data.agents[name]) ? 'active' : ''}" aria-hidden="true"></span>
        </a>
    `).join('');
}

function createEventStream(url, onData, onError, fallbackIntervalMs, fallbackFn) {
    if (typeof EventSource === 'undefined') {
        setLiveIndicator('warning');
        if (typeof fallbackFn === 'function') {
            fallbackFn();
            const fallbackId = setInterval(fallbackFn, fallbackIntervalMs);
            return { close() { clearInterval(fallbackId); } };
        }
        return { close() {} };
    }

    let fallbackId = null;
    const source = new EventSource(url);

    source.onmessage = (event) => {
        try {
            setLiveIndicator('active');
            onData(JSON.parse(event.data));
        } catch (error) {
            if (typeof onError === 'function') {
                onError(error);
            }
        }
    };

    source.onerror = () => {
        source.close();
        if (typeof onError === 'function') {
            onError(new Error(`Stream failed: ${url}`));
        }
        if (typeof fallbackFn === 'function' && !fallbackId) {
            setLiveIndicator('warning');
            fallbackFn();
            fallbackId = setInterval(fallbackFn, fallbackIntervalMs);
        } else {
            setLiveIndicator('offline');
        }
    };

    return {
        close() {
            source.close();
            if (fallbackId) {
                clearInterval(fallbackId);
            }
        }
    };
}

function initializeTabGroups(root = document) {
    root.querySelectorAll('[data-tab-group]').forEach((group) => {
        const buttons = group.querySelectorAll('[data-tab-target]');
        const panels = group.querySelectorAll('[data-tab-panel]');
        if (!buttons.length || !panels.length) {
            return;
        }

        const activate = (target) => {
            buttons.forEach((button) => {
                button.classList.toggle('active', button.getAttribute('data-tab-target') === target);
            });
            panels.forEach((panel) => {
                panel.classList.toggle('active', panel.getAttribute('data-tab-panel') === target);
            });
            window.dispatchEvent(new CustomEvent('tabchange', {
                detail: {
                    group: group.getAttribute('data-tab-group-name') || '',
                    target: target
                }
            }));
        };

        const initial = group.getAttribute('data-tab-default') || buttons[0].getAttribute('data-tab-target');
        activate(initial);

        buttons.forEach((button) => {
            button.addEventListener('click', () => activate(button.getAttribute('data-tab-target')));
        });
    });
}

function setCollapseState(block, expanded) {
    const body = block.querySelector('[data-collapse-body]');
    const toggle = block.querySelector('[data-collapse-toggle]');
    const label = block.querySelector('.collapse-toggle-label');
    if (!body || !toggle) {
        return;
    }

    block.classList.toggle('is-collapsed', !expanded);
    body.hidden = !expanded;
    toggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    if (label) {
        label.innerText = expanded ? 'Hide' : 'Show';
    }

    const storageKey = block.getAttribute('data-collapsible-key');
    if (storageKey) {
        localStorage.setItem(`collapse:${storageKey}`, expanded ? 'expanded' : 'collapsed');
    }
}

function initializeCollapsibles(root = document) {
    root.querySelectorAll('[data-collapsible]').forEach((block) => {
        const toggle = block.querySelector('[data-collapse-toggle]');
        const body = block.querySelector('[data-collapse-body]');
        if (!toggle || !body) {
            return;
        }

        const storageKey = block.getAttribute('data-collapsible-key');
        const saved = storageKey ? localStorage.getItem(`collapse:${storageKey}`) : null;
        const expanded = saved !== 'collapsed';
        setCollapseState(block, expanded);

        toggle.addEventListener('click', () => {
            setCollapseState(block, block.classList.contains('is-collapsed'));
            window.dispatchEvent(new Event('resize'));
        });
    });
}

// Initialize everything
initializeTheme();
initializeSidebar();
initializeDensity();

window.addEventListener('DOMContentLoaded', () => {
    initializeTabGroups();
    initializeCollapsibles();
    
    const themeSelect = document.getElementById('theme-select');
    if (themeSelect) {
        themeSelect.addEventListener('change', (event) => {
            applyTheme(event.target.value);
        });
    }
    
    const modal = document.getElementById('app-modal');
    const confirmButton = document.getElementById('app-modal-confirm');
    const cancelButton = document.getElementById('app-modal-cancel');
    if (modal && confirmButton && cancelButton) {
        modal.addEventListener('click', (event) => {
            if (event.target.closest('[data-modal-close]')) {
                closeAppModal(false);
            }
        });
        confirmButton.addEventListener('click', () => closeAppModal(true));
        cancelButton.addEventListener('click', () => closeAppModal(false));
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && !modal.hidden) {
                closeAppModal(false);
            }
        });
    }
    
    const logoutLink = document.getElementById('logout-link');
    if (logoutLink) {
        logoutLink.addEventListener('click', async (event) => {
            event.preventDefault();
            const confirmed = await showConfirmModal('Log out of the LikePilot dashboard?', {
                title: 'Log out',
                confirmLabel: 'Log out',
                cancelLabel: 'Stay here',
                confirmClass: 'btn-danger'
            });
            if (confirmed) {
                window.location.href = logoutLink.href;
            }
        });
    }
    
    document.addEventListener('click', (event) => {
        const quickLink = event.target.closest('[data-quick-agent]');
        if (quickLink) {
            localStorage.setItem('focusedAgentName', quickLink.getAttribute('data-quick-agent'));
        }
    });
    
    if (document.getElementById('agent-quick-switch')) {
        createEventStream(
            '/api/stream/status',
            renderAgentQuickSwitch,
            () => setLoadingState(document.getElementById('agent-quick-switch'), 'Quick switch offline.'),
            4000,
            () => fetchJson('/api/status').then(renderAgentQuickSwitch).catch(() => {})
        );
    }
});
