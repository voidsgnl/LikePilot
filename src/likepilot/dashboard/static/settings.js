(function () {
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

    const SITES = [
        'Like4Like',
        'KingdomLikes',
        'YouLikeHits'
    ];

    const DEFAULT_IG_COMMENT_TEMPLATES = [
        '🔥🔥',
        '😍😍',
        '👏👏',
        '🙌🙌',
        '❤️❤️'
    ].join('\n');

    function platformOptions(selected, includeBlank) {
        const options = [];
        if (includeBlank) {
            options.push(`<option value="">Manual choice</option>`);
        }
        return options.concat(PLATFORMS.map((platform) => `
            <option value="${escapeHtml(platform)}" ${platform === selected ? 'selected' : ''}>${escapeHtml(platform)}</option>
        `)).join('');
    }

    function siteOptions(selected) {
        return SITES.map((site) => `
            <option value="${escapeHtml(site)}" ${site === selected ? 'selected' : ''}>${escapeHtml(site)}</option>
        `).join('');
    }

    function summarizeChain(value) {
        return value && value.trim() ? value : 'No chain selected';
    }

    function updateChainSummary(target) {
        if (!target) {
            return;
        }
        const row = target.closest('.chain-input-row');
        if (!row) {
            return;
        }
        const summary = row.nextElementSibling && row.nextElementSibling.classList.contains('section-subtle')
            ? row.nextElementSibling
            : null;
        if (summary) {
            summary.innerText = summarizeChain(target.value || '');
        }
    }

    async function pickChain(targetId) {
        const target = document.getElementById(targetId);
        if (!target || target.disabled) {
            return;
        }
        const selected = new Set(
            String(target.value || '')
                .split(',')
                .map((item) => item.trim())
                .filter(Boolean)
        );
        const html = `
            <div class="chain-picker">
                <div class="section-subtle">Choose the order you want the agent to try after exhaustion.</div>
                <div class="chain-picker-list">
                    ${PLATFORMS.map((platform, index) => `
                        <label class="chain-option">
                            <input type="checkbox" value="${escapeHtml(platform)}" ${selected.has(platform) ? 'checked' : ''}>
                            <span class="chain-order">${index + 1}</span>
                            <span>${escapeHtml(platform)}</span>
                        </label>
                    `).join('')}
                </div>
            </div>
        `;

        const confirmed = await openAppModal({
            title: 'Select platform chain',
            html: html,
            confirmLabel: 'Use selected',
            cancelLabel: 'Cancel',
            confirmClass: 'btn-primary'
        });
        if (!confirmed) {
            return;
        }

        const body = document.getElementById('app-modal-body');
        const chosen = body
            ? Array.from(body.querySelectorAll('input[type="checkbox"]:checked')).map((input) => input.value)
            : [];
        target.value = chosen.join(', ');
        updateChainSummary(target);
        target.dispatchEvent(new Event('change', { bubbles: true }));
    }

    async function deployAgent() {
        const name = document.getElementById('new-agent-name').value.trim();
        const profile = document.getElementById('new-agent-profile').value.trim();
        const proxy = document.getElementById('new-agent-proxy').value.trim();
        const site = document.getElementById('new-agent-site').value.trim();
        const fallback = document.getElementById('new-agent-fallback').value.trim();
        const chain = document.getElementById('new-agent-chain').value.trim();
        const commentTemplates = document.getElementById('new-agent-comment-templates').value.trim();

        if (!name || !profile) {
            await showAlertModal('Agent name and profile are required.', {
                title: 'Missing fields',
                confirmLabel: 'Close'
            });
            return;
        }

        fetchJson('/api/agents/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                profile: profile,
                proxy: proxy || null,
                site: site,
                fallback_platform: fallback || null,
                fallback_chain: chain || null,
                comment_templates: commentTemplates || DEFAULT_IG_COMMENT_TEMPLATES
            })
        }).then((response) => {
            document.getElementById('new-agent-name').value = '';
            document.getElementById('new-agent-profile').value = '';
            document.getElementById('new-agent-proxy').value = '';
            document.getElementById('new-agent-fallback').value = '';
            document.getElementById('new-agent-chain').value = '';
            document.getElementById('new-agent-comment-templates').value = DEFAULT_IG_COMMENT_TEMPLATES;
            loadAgents();
            return showSuccessModal(response.message || `${name} added.`, {
                title: 'Agent created',
                confirmLabel: 'Close'
            });
        }).catch(() => {
            setLoadingState(document.getElementById('settings-feedback'), 'Failed to add agent.');
        });
    }

    async function terminateAgent(name) {
        const confirmed = await showConfirmModal(`Remove ${name}? This deletes its logs and local credit history.`, {
            title: 'Delete agent',
            confirmLabel: 'Delete',
            cancelLabel: 'Keep agent',
            confirmClass: 'btn-danger'
        });
        if (!confirmed) {
            return;
        }

        fetchJson('/api/agents/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name })
        }).then((response) => {
            loadAgents();
            return showSuccessModal(response.message || `${name} removed.`, {
                title: 'Agent removed',
                confirmLabel: 'Close'
            });
        }).catch(() => {
            setLoadingState(document.getElementById('settings-feedback'), 'Failed to remove agent.');
        });
    }

    function saveAgent(currentName) {
        const nameInput = document.getElementById(`edit-name-${currentName}`);
        const profileInput = document.getElementById(`edit-profile-${currentName}`);
        const proxyInput = document.getElementById(`edit-proxy-${currentName}`);
        const siteInput = document.getElementById(`edit-site-${currentName}`);
        const fallbackInput = document.getElementById(`edit-fallback-${currentName}`);
        const chainInput = document.getElementById(`edit-chain-${currentName}`);
        const commentTemplatesInput = document.getElementById(`edit-comment-templates-${currentName}`);
        const name = nameInput.value.trim();
        const profile = profileInput.value.trim();
        const proxy = proxyInput.value.trim();
        const site = siteInput.value.trim();
        const fallback = fallbackInput.value.trim();
        const chain = chainInput.value.trim();
        const commentTemplates = commentTemplatesInput.value.trim();

        if (!name || !profile) {
            setLoadingState(document.getElementById('settings-feedback'), 'Agent name and profile are required.');
            return;
        }

        fetchJson('/api/agents/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_name: currentName,
                name: name,
                profile: profile,
                proxy: proxy || null,
                site: site,
                fallback_platform: fallback || null,
                fallback_chain: chain || null,
                comment_templates: commentTemplates || DEFAULT_IG_COMMENT_TEMPLATES
            })
        }).then((response) => {
            loadAgents();
            return showSuccessModal(response.message || `${name} updated.`, {
                title: 'Agent updated',
                confirmLabel: 'Close'
            });
        }).catch((error) => {
            setLoadingState(document.getElementById('settings-feedback'), error.message || 'Failed to update agent.');
        });
    }
function renderAgents(data) {
    const list = document.getElementById('active-agents-list');
    const feedback = document.getElementById('settings-feedback');
    if (!list || !feedback) return;
    const items = Object.entries(data.agents);
    const statusChipClass = (status) => status === 'Running'
        ? 'chip chip-running status-running'
        : (status === 'Awaiting Login' || status === 'Login Success' || status === 'Awaiting Social Login' || status === 'Awaiting Switch')
            ? 'chip chip-waiting'
            : 'chip chip-stopped';
    const statusLabel = (status) => status === 'Awaiting Login'
        ? 'Awaiting Login'
        : status === 'Login Success'
            ? 'Login Success'
            : status === 'Awaiting Social Login'
                ? 'Social login required'
                : status;

    // Check if user is currently interacting with any element in the list
    const activeEl = document.activeElement;
    const isInteracting = list.contains(activeEl);

    if (isInteracting) {
        // Only update status chips if user is interacting, to avoid resetting inputs
        items.forEach(([name, status]) => {
            const card = list.querySelector(`.settings-agent-card[data-agent-name="${name}"]`);
            if (card) {
                const chip = card.querySelector('.chip');
                if (chip) {
                    chip.className = statusChipClass(status.status);
                    chip.textContent = statusLabel(status.status);
                }
            }
        });
        return;
    }

    const renderKey = JSON.stringify(
        items.map(([name, status]) => ({
            name: name,
            status: status.status,
            chrome_profile: status.chrome_profile,
            proxy: status.proxy || '',
            site: status.site || 'Like4Like',
            fallback_platform: status.fallback_platform || '',
            fallback_chain: status.fallback_chain || '',
            comment_templates: status.comment_templates || ''
        }))
    );

    if (list.getAttribute('data-render-key') === renderKey) {
        feedback.innerHTML = items.length
            ? `<span class="section-subtle">${items.length} configured agent${items.length === 1 ? '' : 's'} available. Use Fallback for one-step routing or Chain for a custom exhaustion sequence.</span>`
            : `<span class="section-subtle">Create your first agent to start using the workspace.</span>`;
        return;
    }

    list.innerHTML = items.length
        ? items.map(([name, status]) => `
            <div class="event-item settings-agent-card" data-agent-name="${escapeHtml(name)}">
                    <div class="settings-agent-fields">
                        <div>
                            <label class="section-subtle field-label" for="edit-name-${escapeHtml(name)}">Agent</label>
                            <input type="text" id="edit-name-${escapeHtml(name)}" value="${escapeHtml(name)}" ${status.status !== 'Stopped' ? 'disabled' : ''}>
                        </div>
                        <div>
                            <label class="section-subtle field-label" for="edit-profile-${escapeHtml(name)}">Profile</label>
                            <input type="text" id="edit-profile-${escapeHtml(name)}" value="${escapeHtml(status.chrome_profile)}" ${status.status !== 'Stopped' ? 'disabled' : ''}>
                        </div>
                        <div>
                            <label class="section-subtle field-label" for="edit-proxy-${escapeHtml(name)}">Proxy</label>
                            <input type="text" id="edit-proxy-${escapeHtml(name)}" value="${escapeHtml(status.proxy || '')}" placeholder="Optional proxy" ${status.status !== 'Stopped' ? 'disabled' : ''}>
                        </div>
                        <div>
                            <label class="section-subtle field-label" for="edit-site-${escapeHtml(name)}">Site</label>
                            <select id="edit-site-${escapeHtml(name)}" ${status.status !== 'Stopped' ? 'disabled' : ''}>
                                ${siteOptions(status.site || 'Like4Like')}
                            </select>
                        </div>
                        <div>
                            <label class="section-subtle field-label" for="edit-fallback-${escapeHtml(name)}">Fallback</label>
                            <select id="edit-fallback-${escapeHtml(name)}" ${status.status !== 'Stopped' ? 'disabled' : ''}>
                                ${platformOptions(status.fallback_platform || '', true)}
                            </select>
                        </div>
                        <div>
                            <label class="section-subtle field-label" for="edit-chain-${escapeHtml(name)}">Chain</label>
                            <div class="chain-input-row">
                                <input type="text" id="edit-chain-${escapeHtml(name)}" value="${escapeHtml(status.fallback_chain || '')}" placeholder="No chain selected" readonly ${status.status !== 'Stopped' ? 'disabled' : ''}>
                                <button type="button" class="btn-secondary btn-compact" data-pick-chain="edit-chain-${escapeHtml(name)}" ${status.status !== 'Stopped' ? 'disabled' : ''}>Choose</button>
                            </div>
                            <div class="section-subtle">${escapeHtml(summarizeChain(status.fallback_chain || ''))}</div>
                        </div>
                        <div class="form-grid-wide">
                            <label class="section-subtle field-label" for="edit-comment-templates-${escapeHtml(name)}">Instagram comment emojis</label>
                            <textarea id="edit-comment-templates-${escapeHtml(name)}" rows="4" placeholder="One comment per line" ${status.status !== 'Stopped' ? 'disabled' : ''}>${escapeHtml(status.comment_templates || DEFAULT_IG_COMMENT_TEMPLATES)}</textarea>
                            <div class="section-subtle">Fallback comments used by IG Comments when no required text is provided.</div>
                        </div>
                    </div>
                    <div class="settings-agent-meta">
                        <span class="${statusChipClass(status.status)}">${escapeHtml(statusLabel(status.status))}</span>
                        <div class="actions">
                            <button class="btn-primary btn-compact" data-save-agent="${escapeHtml(name)}" ${status.status !== 'Stopped' ? 'disabled' : ''}>Save</button>
                            <button class="btn-danger btn-compact" data-remove-agent="${escapeHtml(name)}">Remove</button>
                        </div>
                    </div>
                </div>
            `).join('')
            : `<div class="section-subtle">No agents configured yet.</div>`;
        list.setAttribute('data-render-key', renderKey);
        feedback.innerHTML = items.length
            ? `<span class="section-subtle">${items.length} configured agent${items.length === 1 ? '' : 's'} available. Use Fallback for one-step routing or Chain for a custom exhaustion sequence.</span>`
            : `<span class="section-subtle">Create your first agent to start using the workspace.</span>`;
    }

    function loadBrowserSetting() {
        const select = document.getElementById('default-browser');
        const feedback = document.getElementById('browser-setting-feedback');
        if (!select || !feedback) return;
        fetchJson('/api/settings/browser').then((data) => {
            select.value = data.browser || 'chrome';
            feedback.textContent = 'Current default: ' + (data.browser || 'chrome').toUpperCase();
        }).catch(() => { feedback.textContent = 'Unable to load browser setting.'; });
    }

    function saveBrowserSetting() {
        const select = document.getElementById('default-browser');
        const feedback = document.getElementById('browser-setting-feedback');
        if (!select || !feedback) return;
        const button = document.querySelector('[data-save-browser]');
        if (button) button.disabled = true;
        fetchJson('/api/settings/browser', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ browser: select.value })
        }).then((data) => {
            feedback.textContent = data.message || 'Browser setting saved.';
            return showSuccessModal(data.message || 'Browser setting saved.', {
                title: 'Browser setting updated', confirmLabel: 'Close'
            });
        }).catch((error) => {
            feedback.textContent = error.message || 'Unable to save browser setting.';
        }).finally(() => { if (button) button.disabled = false; });
    }

    function loadProviderLoginSettings() {
        const feedback = document.getElementById('provider-login-feedback');
        if (!feedback) return;
        fetchJson('/api/settings/providers').then((data) => {
            Object.entries(data.providers || {}).forEach(([site, config]) => {
                const card = document.querySelector(`[data-provider-login="${site}"]`);
                if (!card) return;
                const enabled = card.querySelector('[data-provider-login-enabled]');
                const username = card.querySelector('[data-provider-login-username]');
                const password = card.querySelector('[data-provider-login-password]');
                const status = card.querySelector(`[data-provider-login-status="${site}"]`);
                enabled.checked = Boolean(config.enabled);
                username.value = config.username || '';
                password.value = '';
                password.placeholder = config.has_password ? 'Saved. Leave blank to keep it.' : 'Provider password';
                status.textContent = config.enabled ? 'Auto login enabled' : 'Manual login';
            });
            feedback.textContent = '';
        }).catch((error) => {
            feedback.textContent = error.message || 'Unable to load provider login settings.';
        });
    }

    function saveProviderLoginSettings(site) {
        const card = document.querySelector(`[data-provider-login="${site}"]`);
        const feedback = document.getElementById('provider-login-feedback');
        if (!card || !feedback) return;
        const enabled = card.querySelector('[data-provider-login-enabled]').checked;
        const username = card.querySelector('[data-provider-login-username]').value.trim();
        const password = card.querySelector('[data-provider-login-password]').value;
        const button = card.querySelector('[data-save-provider-login]');
        if (button) button.disabled = true;

        fetchJson('/api/settings/providers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                site,
                enabled,
                username,
                ...(password ? { password } : {})
            })
        }).then((data) => {
            card.querySelector('[data-provider-login-password]').value = '';
            card.querySelector('[data-provider-login-password]').placeholder = data.provider.has_password
                ? 'Saved. Leave blank to keep it.'
                : 'Provider password';
            card.querySelector(`[data-provider-login-status="${site}"]`).textContent = enabled
                ? 'Auto login enabled'
                : 'Manual login';
            feedback.textContent = data.message || 'Provider login settings saved.';
        }).catch((error) => {
            feedback.textContent = error.message || 'Unable to save provider login settings.';
        }).finally(() => {
            if (button) button.disabled = false;
        });
    }

    function loadAgents() {
        fetchJson('/api/status')
            .then(renderAgents)
            .catch(() => {
                setLoadingState(document.getElementById('settings-feedback'), 'Unable to load configuration right now.');
            });
    }

    document.addEventListener('click', (event) => {
        const providerLoginButton = event.target.closest('[data-save-provider-login]');
        if (providerLoginButton) {
            saveProviderLoginSettings(providerLoginButton.getAttribute('data-save-provider-login'));
            return;
        }

        const browserButton = event.target.closest('[data-save-browser]');
        if (browserButton) { saveBrowserSetting(); return; }

        const addButton = event.target.closest('[data-add-agent]');
        if (addButton) {
            void deployAgent();
            return;
        }

        const removeButton = event.target.closest('[data-remove-agent]');
        if (removeButton) {
            void terminateAgent(removeButton.getAttribute('data-remove-agent'));
            return;
        }

        const saveButton = event.target.closest('[data-save-agent]');
        if (saveButton) {
            saveAgent(saveButton.getAttribute('data-save-agent'));
            return;
        }

        const chainButton = event.target.closest('[data-pick-chain]');
        if (chainButton) {
            void pickChain(chainButton.getAttribute('data-pick-chain'));
        }
    });

    loadBrowserSetting();
    loadProviderLoginSettings();

    if (document.getElementById('active-agents-list')) {
        createEventStream(
            '/api/stream/status',
            renderAgents,
            () => setLoadingState(document.getElementById('settings-feedback'), 'Live configuration stream unavailable. Falling back to polling.'),
            5000,
            loadAgents
        );
    }

    const newCommentTemplates = document.getElementById('new-agent-comment-templates');
    if (newCommentTemplates && !newCommentTemplates.value.trim()) {
        newCommentTemplates.value = DEFAULT_IG_COMMENT_TEMPLATES;
    }
})();
