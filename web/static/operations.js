(function () {
    const state = {
        database: {
            info: null,
            tables: [],
            relationships: [],
            selectedTable: '',
            preview: null,
            view: 'data'
        },
        logs: {
            files: [],
            selectedLog: '',
            content: null
        },
        diagnostics: {
            captures: [],
            selectedCapture: '',
            capture: null
        }
    };

    let schemaLineFrame = 0;

    function formatBytes(value) {
        const bytes = Number(value || 0);
        if (bytes <= 0) {
            return '0 B';
        }
        const units = ['B', 'KB', 'MB', 'GB'];
        const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
        const scaled = bytes / Math.pow(1024, exponent);
        return `${scaled >= 10 || exponent === 0 ? scaled.toFixed(0) : scaled.toFixed(1)} ${units[exponent]}`;
    }

    function setFeedback(message) {
        const feedback = document.getElementById('operations-feedback');
        if (feedback) {
            feedback.innerHTML = `<span class="section-subtle">${escapeHtml(message)}</span>`;
        }
    }

    function formatCellValue(value) {
        if (value === null || value === undefined) {
            return '<span class="section-subtle">NULL</span>';
        }
        if (typeof value === 'object') {
            return `<span class="mono">${escapeHtml(JSON.stringify(value))}</span>`;
        }
        const text = String(value);
        if (!text) {
            return '<span class="section-subtle">(empty)</span>';
        }
        return `<span class="ops-cell">${escapeHtml(text)}</span>`;
    }

    function selectedTableRecord() {
        return state.database.tables.find((table) => table.name === state.database.selectedTable) || null;
    }

    function setDatabaseView(view) {
        state.database.view = view === 'schema' ? 'schema' : 'data';
        const preview = document.getElementById('ops-db-preview');
        const schema = document.getElementById('ops-db-schema');
        const dataButton = document.getElementById('ops-db-view-data');
        const schemaButton = document.getElementById('ops-db-view-schema');
        if (preview) {
            preview.hidden = state.database.view !== 'data';
        }
        if (schema) {
            schema.hidden = state.database.view !== 'schema';
        }
        if (dataButton) {
            dataButton.classList.toggle('active', state.database.view === 'data');
        }
        if (schemaButton) {
            schemaButton.classList.toggle('active', state.database.view === 'schema');
        }
        updateDatabaseMeta();
        if (state.database.view === 'schema') {
            scheduleSchemaLineRender();
        }
    }

    function updateSummaryCards() {
        const dbCount = document.getElementById('ops-db-count');
        const dbMeta = document.getElementById('ops-db-meta');
        const logCount = document.getElementById('ops-log-count');
        const logMeta = document.getElementById('ops-log-summary-meta');
        const diagnosticCount = document.getElementById('ops-diagnostic-count');
        const diagnosticMeta = document.getElementById('ops-diagnostic-summary-meta');

        if (dbCount) {
            dbCount.innerText = String((state.database.tables || []).length);
        }
        if (dbMeta) {
            const relationshipCount = Number(state.database.info?.relationship_count || 0);
            dbMeta.innerText = state.database.info
                ? `${formatBytes(state.database.info.size_bytes)} SQLite file • ${relationshipCount} link${relationshipCount === 1 ? '' : 's'}`
                : 'Database not loaded yet.';
        }
        if (logCount) {
            logCount.innerText = String((state.logs.files || []).length);
        }
        if (logMeta) {
            const latest = (state.logs.files || []).find((item) => item.is_latest);
            logMeta.innerText = latest
                ? `Latest file: ${latest.name}`
                : 'No log inventory yet.';
        }
        if (diagnosticCount) {
            diagnosticCount.innerText = String((state.diagnostics.captures || []).length);
        }
        if (diagnosticMeta) {
            diagnosticMeta.innerText = state.diagnostics.captures.length
                ? `Newest capture: ${state.diagnostics.captures[0].modified_at}`
                : 'No diagnostic captures loaded.';
        }
    }

    function renderDatabaseList() {
        const host = document.getElementById('ops-db-list');
        const summary = document.getElementById('ops-db-summary');
        if (!host || !summary) {
            return;
        }

        const info = state.database.info;
        if (info) {
            summary.innerHTML = `
                <span class="mono">${escapeHtml(info.path)}</span><br>
                ${state.database.tables.length} table${state.database.tables.length === 1 ? '' : 's'} • ${Number(info.relationship_count || 0)} relationship${Number(info.relationship_count || 0) === 1 ? '' : 's'} • ${formatBytes(info.size_bytes)}
            `;
        } else {
            summary.innerText = 'Loading database details.';
        }

        if (!state.database.tables.length) {
            host.innerHTML = `<div class="empty-state">No SQLite tables found.</div>`;
            return;
        }

        host.innerHTML = state.database.tables.map((table) => {
            const relationCount = (table.foreign_keys || []).length;
            return `
                <button
                    type="button"
                    class="ops-list-item ${table.name === state.database.selectedTable ? 'active' : ''}"
                    data-select-table="${escapeHtml(table.name)}"
                >
                    <span class="ops-list-title">${escapeHtml(table.name)}</span>
                    <span class="ops-list-meta">${table.row_count} row${table.row_count === 1 ? '' : 's'} • ${table.columns.length} col${table.columns.length === 1 ? '' : 's'}${relationCount ? ` • ${relationCount} link${relationCount === 1 ? '' : 's'}` : ''}</span>
                </button>
            `;
        }).join('');
    }

    function updateDatabaseMeta() {
        const meta = document.getElementById('ops-db-table-meta');
        const schemaMeta = document.getElementById('ops-db-schema-meta');
        if (!meta || !schemaMeta) {
            return;
        }

        const selected = selectedTableRecord();
        if (state.database.view === 'schema') {
            if (selected) {
                const inbound = state.database.relationships.filter((item) => item.to_table === selected.name).length;
                const outbound = state.database.relationships.filter((item) => item.from_table === selected.name).length;
                meta.innerHTML = `
                    <span class="mono">${escapeHtml(selected.name)}</span> • ${selected.columns.length} column${selected.columns.length === 1 ? '' : 's'} • ${selected.row_count} row${selected.row_count === 1 ? '' : 's'} • ${inbound} inbound • ${outbound} outbound
                `;
            } else {
                meta.innerText = 'Schema view maps table structure and relationships.';
            }
        } else if (state.database.preview) {
            const table = state.database.preview;
            meta.innerHTML = `
                <span class="mono">${escapeHtml(table.table)}</span> • ${table.row_count} row${table.row_count === 1 ? '' : 's'} • ${table.columns.length} column${table.columns.length === 1 ? '' : 's'}
            `;
        } else {
            meta.innerText = 'Choose a table to inspect.';
        }

        const selectedLabel = selected ? selected.name : 'all tables';
        schemaMeta.innerText = `${state.database.tables.length} tables • ${state.database.relationships.length} relationships • focus: ${selectedLabel}`;
    }

    function renderDatabasePreview() {
        const preview = document.getElementById('ops-db-preview');
        if (!preview) {
            return;
        }

        const table = state.database.preview;
        if (!table) {
            preview.innerHTML = 'Choose a table to inspect.';
            preview.classList.add('empty-state');
            updateDatabaseMeta();
            return;
        }

        if (!table.rows.length) {
            preview.innerHTML = '<div class="empty-state">This table is empty.</div>';
            preview.classList.add('empty-state');
            updateDatabaseMeta();
            return;
        }

        preview.classList.remove('empty-state');
        preview.innerHTML = `
            <div class="ops-chip-row">
                ${table.columns.map((column) => `
                    <span class="chip">${escapeHtml(column.name)}${column.type ? ` • ${escapeHtml(column.type)}` : ''}</span>
                `).join('')}
            </div>
            <div class="table-wrap">
                <table class="data-table">
                    <thead>
                        <tr>${table.columns.map((column) => `<th>${escapeHtml(column.name)}</th>`).join('')}</tr>
                    </thead>
                    <tbody>
                        ${table.rows.map((row) => `
                            <tr>
                                ${table.columns.map((column) => `<td>${formatCellValue(row[column.name])}</td>`).join('')}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        updateDatabaseMeta();
    }

    function renderSchemaView() {
        const host = document.getElementById('ops-schema-grid');
        if (!host) {
            return;
        }

        if (!state.database.tables.length) {
            host.innerHTML = `<div class="empty-state">No schema data is available.</div>`;
            updateDatabaseMeta();
            return;
        }

        host.innerHTML = state.database.tables.map((table) => `
            <button
                type="button"
                class="ops-schema-card ${table.name === state.database.selectedTable ? 'active' : ''}"
                data-select-table="${escapeHtml(table.name)}"
                data-schema-table="${escapeHtml(table.name)}"
            >
                <div class="ops-schema-card-header">
                    <span class="ops-schema-card-title">${escapeHtml(table.name)}</span>
                    <span class="ops-schema-card-count">${table.row_count}</span>
                </div>
                <div class="ops-schema-card-body">
                    ${table.columns.map((column) => `
                        <div
                            class="ops-schema-column ${column.primary_key ? 'pk' : ''}"
                            data-column-key="${escapeHtml(`${table.name}.${column.name}`)}"
                        >
                            <span class="ops-schema-column-icon">${column.primary_key ? '◆' : '◇'}</span>
                            <span class="ops-schema-column-name">${escapeHtml(column.name)}</span>
                            <span class="ops-schema-column-type">${escapeHtml(column.type || 'value')}</span>
                        </div>
                    `).join('')}
                </div>
            </button>
        `).join('');

        updateDatabaseMeta();
        scheduleSchemaLineRender();
    }

    function scheduleSchemaLineRender() {
        if (schemaLineFrame) {
            cancelAnimationFrame(schemaLineFrame);
        }
        schemaLineFrame = requestAnimationFrame(() => {
            schemaLineFrame = 0;
            drawSchemaLines();
        });
    }

    function drawSchemaLines() {
        const stage = document.getElementById('ops-schema-stage');
        const svg = document.getElementById('ops-schema-lines');
        if (!stage || !svg || state.database.view !== 'schema') {
            return;
        }

        const stageRect = stage.getBoundingClientRect();
        const width = Math.max(1, Math.ceil(stage.scrollWidth || stage.clientWidth || stageRect.width));
        const height = Math.max(1, Math.ceil(stage.scrollHeight || stage.clientHeight || stageRect.height));
        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
        svg.setAttribute('width', String(width));
        svg.setAttribute('height', String(height));

        const lines = [];
        state.database.relationships.forEach((relationship) => {
            const from = stage.querySelector(`[data-column-key="${CSS.escape(`${relationship.from_table}.${relationship.from_column}`)}"]`);
            const to = stage.querySelector(`[data-column-key="${CSS.escape(`${relationship.to_table}.${relationship.to_column}`)}"]`);
            if (!from || !to) {
                return;
            }

            const fromRect = from.getBoundingClientRect();
            const toRect = to.getBoundingClientRect();
            const startX = fromRect.right - stageRect.left + stage.scrollLeft;
            const startY = fromRect.top - stageRect.top + stage.scrollTop + (fromRect.height / 2);
            const endX = toRect.left - stageRect.left + stage.scrollLeft;
            const endY = toRect.top - stageRect.top + stage.scrollTop + (toRect.height / 2);
            const gap = Math.max(36, Math.abs(endX - startX) * 0.35);
            const selected = relationship.from_table === state.database.selectedTable || relationship.to_table === state.database.selectedTable;
            lines.push(`
                <path
                    d="M ${startX} ${startY} C ${startX + gap} ${startY}, ${endX - gap} ${endY}, ${endX} ${endY}"
                    class="ops-schema-line ${selected ? 'active' : ''}"
                />
            `);
        });

        svg.innerHTML = lines.join('');
    }

    function renderLogList() {
        const host = document.getElementById('ops-log-list');
        if (!host) {
            return;
        }
        if (!state.logs.files.length) {
            host.innerHTML = `<div class="empty-state">No log files were found in logs/.</div>`;
            return;
        }
        host.innerHTML = state.logs.files.map((file) => `
            <button
                type="button"
                class="ops-list-item ${file.name === state.logs.selectedLog ? 'active' : ''}"
                data-select-log="${escapeHtml(file.name)}"
            >
                <span class="ops-list-title">${escapeHtml(file.name)}</span>
                <span class="ops-list-meta">${formatBytes(file.size_bytes)} • ${escapeHtml(file.modified_at)}${file.is_latest ? ' • latest' : ''}</span>
            </button>
        `).join('');
    }

    function renderLogViewer() {
        const meta = document.getElementById('ops-log-meta');
        const content = document.getElementById('ops-log-content');
        const clearButton = document.getElementById('ops-clear-log');
        const deleteButton = document.getElementById('ops-delete-log');
        if (!meta || !content || !clearButton || !deleteButton) {
            return;
        }

        clearButton.disabled = !state.logs.selectedLog;
        deleteButton.disabled = !state.logs.selectedLog;

        if (!state.logs.content) {
            meta.innerText = 'Select a log file to view its latest lines.';
            content.textContent = 'Select a log file to view its latest lines.';
            return;
        }

        meta.innerText = `${state.logs.content.name} • showing last ${state.logs.content.tail} lines • total ${state.logs.content.line_count}`;
        content.textContent = state.logs.content.content || '';
    }

    function renderDiagnosticList() {
        const host = document.getElementById('ops-diagnostic-list');
        if (!host) {
            return;
        }
        if (!state.diagnostics.captures.length) {
            host.innerHTML = `<div class="empty-state">No diagnostic captures are available.</div>`;
            return;
        }
        host.innerHTML = state.diagnostics.captures.map((capture) => `
            <button
                type="button"
                class="ops-list-item ${capture.id === state.diagnostics.selectedCapture ? 'active' : ''}"
                data-select-diagnostic="${escapeHtml(capture.id)}"
            >
                <span class="ops-list-title">${escapeHtml(capture.label)}</span>
                <span class="ops-list-meta">${escapeHtml(capture.modified_at)} • ${capture.files.length} file${capture.files.length === 1 ? '' : 's'}</span>
            </button>
        `).join('');
    }

    function renderDiagnosticPreview() {
        const meta = document.getElementById('ops-diagnostic-meta');
        const preview = document.getElementById('ops-diagnostic-preview');
        const deleteButton = document.getElementById('ops-delete-diagnostic');
        if (!meta || !preview || !deleteButton) {
            return;
        }

        deleteButton.disabled = !state.diagnostics.capture;

        const capture = state.diagnostics.capture;
        if (!capture) {
            meta.innerText = 'Select a capture to preview its contents.';
            preview.classList.add('empty-state');
            preview.innerHTML = 'Select a capture to preview its contents.';
            return;
        }

        meta.innerText = `${capture.label} • ${capture.modified_at} • ${capture.files.length} file${capture.files.length === 1 ? '' : 's'}`;
        preview.classList.remove('empty-state');
        preview.innerHTML = `
            <div class="ops-toolbar">
                ${capture.html_file ? `<a class="btn-secondary btn-compact" href="/api/operations/diagnostics/file/${encodeURIComponent(capture.html_file)}" target="_blank" rel="noopener noreferrer">Open HTML</a>` : ''}
                ${capture.image_file ? `<a class="btn-secondary btn-compact" href="/api/operations/diagnostics/file/${encodeURIComponent(capture.image_file)}" target="_blank" rel="noopener noreferrer">Open PNG</a>` : ''}
            </div>
            <div class="ops-chip-row">
                ${capture.files.map((file) => `<span class="chip">${escapeHtml(file.name)}</span>`).join('')}
            </div>
            ${capture.image_file ? `
                <div class="ops-image-frame">
                    <img class="ops-image-preview" src="/api/operations/diagnostics/file/${encodeURIComponent(capture.image_file)}" alt="${escapeHtml(capture.label)}">
                </div>
            ` : '<div class="empty-state">This capture does not include a PNG preview.</div>'}
        `;
    }

    async function loadDatabase() {
        const payload = await fetchJson('/api/operations/database');
        state.database.info = payload.database;
        state.database.tables = payload.tables || [];
        state.database.relationships = payload.relationships || [];
        if (!state.database.selectedTable || !state.database.tables.some((table) => table.name === state.database.selectedTable)) {
            state.database.selectedTable = state.database.tables[0] ? state.database.tables[0].name : '';
        }
        renderDatabaseList();
        renderSchemaView();
        updateSummaryCards();
        if (state.database.selectedTable) {
            await loadDatabaseTable(state.database.selectedTable);
        } else {
            state.database.preview = null;
            renderDatabasePreview();
            updateDatabaseMeta();
        }
    }

    async function loadDatabaseTable(name) {
        state.database.selectedTable = name;
        renderDatabaseList();
        renderSchemaView();
        state.database.preview = await fetchJson(`/api/operations/database/table?name=${encodeURIComponent(name)}`);
        renderDatabasePreview();
    }

    async function loadLogs() {
        const payload = await fetchJson('/api/operations/logs');
        state.logs.files = payload.logs || [];
        if (!state.logs.selectedLog || !state.logs.files.some((file) => file.name === state.logs.selectedLog)) {
            const latest = state.logs.files.find((file) => file.is_latest);
            state.logs.selectedLog = latest ? latest.name : (state.logs.files[0] ? state.logs.files[0].name : '');
        }
        renderLogList();
        updateSummaryCards();
        if (state.logs.selectedLog) {
            await loadLogContent(state.logs.selectedLog);
        } else {
            state.logs.content = null;
            renderLogViewer();
        }
    }

    async function loadLogContent(name) {
        state.logs.selectedLog = name;
        renderLogList();
        state.logs.content = await fetchJson(`/api/operations/logs/read?name=${encodeURIComponent(name)}`);
        renderLogViewer();
    }

    async function loadDiagnostics() {
        const payload = await fetchJson('/api/operations/diagnostics');
        state.diagnostics.captures = payload.captures || [];
        if (!state.diagnostics.selectedCapture || !state.diagnostics.captures.some((capture) => capture.id === state.diagnostics.selectedCapture)) {
            state.diagnostics.selectedCapture = state.diagnostics.captures[0] ? state.diagnostics.captures[0].id : '';
        }
        state.diagnostics.capture = state.diagnostics.captures.find((capture) => capture.id === state.diagnostics.selectedCapture) || null;
        renderDiagnosticList();
        renderDiagnosticPreview();
        updateSummaryCards();
    }

    async function clearSelectedLog() {
        if (!state.logs.selectedLog) {
            return;
        }
        const confirmed = await showConfirmModal(`Clear ${state.logs.selectedLog}? This keeps the file but removes its contents.`, {
            title: 'Clear log file',
            confirmLabel: 'Clear',
            cancelLabel: 'Cancel',
            confirmClass: 'btn-danger'
        });
        if (!confirmed) {
            return;
        }
        const response = await fetchJson('/api/operations/logs/clear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: state.logs.selectedLog })
        });
        await loadLogs();
        await showSuccessModal(response.message || 'Log cleared.', {
            title: 'Log cleared',
            confirmLabel: 'Close'
        });
    }

    async function deleteSelectedLog() {
        if (!state.logs.selectedLog) {
            return;
        }
        const target = state.logs.selectedLog;
        const confirmed = await showConfirmModal(`Delete ${target}? This removes the file from logs/.`, {
            title: 'Delete log file',
            confirmLabel: 'Delete',
            cancelLabel: 'Cancel',
            confirmClass: 'btn-danger'
        });
        if (!confirmed) {
            return;
        }
        const response = await fetchJson('/api/operations/logs/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: target })
        });
        state.logs.selectedLog = '';
        await loadLogs();
        await showSuccessModal(response.message || 'Log deleted.', {
            title: 'Log deleted',
            confirmLabel: 'Close'
        });
    }

    async function deleteSelectedDiagnostic() {
        if (!state.diagnostics.capture) {
            return;
        }
        const target = state.diagnostics.capture;
        const confirmed = await showConfirmModal(`Delete ${target.label}? This removes the grouped HTML and PNG files from diagnostics/.`, {
            title: 'Delete diagnostic capture',
            confirmLabel: 'Delete',
            cancelLabel: 'Cancel',
            confirmClass: 'btn-danger'
        });
        if (!confirmed) {
            return;
        }
        const response = await fetchJson('/api/operations/diagnostics/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ group: target.id })
        });
        state.diagnostics.selectedCapture = '';
        await loadDiagnostics();
        await showSuccessModal(response.message || 'Capture deleted.', {
            title: 'Diagnostics updated',
            confirmLabel: 'Close'
        });
    }

    async function clearAllDiagnostics() {
        const confirmed = await showConfirmModal('Delete every diagnostic capture in diagnostics/? This clears all stored HTML and PNG snapshots.', {
            title: 'Clear diagnostics',
            confirmLabel: 'Delete all',
            cancelLabel: 'Cancel',
            confirmClass: 'btn-danger'
        });
        if (!confirmed) {
            return;
        }
        const response = await fetchJson('/api/operations/diagnostics/clear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        state.diagnostics.selectedCapture = '';
        await loadDiagnostics();
        await showSuccessModal(response.message || 'Diagnostics cleared.', {
            title: 'Diagnostics cleared',
            confirmLabel: 'Close'
        });
    }

    async function initializeOperationsPage() {
        try {
            await Promise.all([loadDatabase(), loadLogs(), loadDiagnostics()]);
            setDatabaseView(state.database.view);
            setFeedback('Operations data is live.');
        } catch (error) {
            setFeedback(error.message || 'Unable to load operations data right now.');
        }
    }

    document.addEventListener('click', (event) => {
        const tableButton = event.target.closest('[data-select-table]');
        if (tableButton) {
            void loadDatabaseTable(tableButton.getAttribute('data-select-table'))
                .then(() => {
                    if (state.database.view === 'schema') {
                        scheduleSchemaLineRender();
                    }
                })
                .catch((error) => setFeedback(error.message || 'Unable to load table preview.'));
            return;
        }

        const logButton = event.target.closest('[data-select-log]');
        if (logButton) {
            void loadLogContent(logButton.getAttribute('data-select-log')).catch((error) => setFeedback(error.message || 'Unable to load log file.'));
            return;
        }

        const diagnosticButton = event.target.closest('[data-select-diagnostic]');
        if (diagnosticButton) {
            state.diagnostics.selectedCapture = diagnosticButton.getAttribute('data-select-diagnostic');
            state.diagnostics.capture = state.diagnostics.captures.find((capture) => capture.id === state.diagnostics.selectedCapture) || null;
            renderDiagnosticList();
            renderDiagnosticPreview();
        }
    });

    document.addEventListener('DOMContentLoaded', () => {
        document.getElementById('ops-refresh-db')?.addEventListener('click', () => {
            void loadDatabase().then(() => setFeedback('Database list refreshed.')).catch((error) => setFeedback(error.message || 'Unable to refresh database.'));
        });
        document.getElementById('ops-refresh-logs')?.addEventListener('click', () => {
            void loadLogs().then(() => setFeedback('Log inventory refreshed.')).catch((error) => setFeedback(error.message || 'Unable to refresh logs.'));
        });
        document.getElementById('ops-refresh-diagnostics')?.addEventListener('click', () => {
            void loadDiagnostics().then(() => setFeedback('Diagnostics refreshed.')).catch((error) => setFeedback(error.message || 'Unable to refresh diagnostics.'));
        });
        document.getElementById('ops-clear-log')?.addEventListener('click', () => {
            void clearSelectedLog().catch((error) => setFeedback(error.message || 'Unable to clear log.'));
        });
        document.getElementById('ops-delete-log')?.addEventListener('click', () => {
            void deleteSelectedLog().catch((error) => setFeedback(error.message || 'Unable to delete log.'));
        });
        document.getElementById('ops-delete-diagnostic')?.addEventListener('click', () => {
            void deleteSelectedDiagnostic().catch((error) => setFeedback(error.message || 'Unable to delete diagnostic capture.'));
        });
        document.getElementById('ops-clear-diagnostics')?.addEventListener('click', () => {
            void clearAllDiagnostics().catch((error) => setFeedback(error.message || 'Unable to clear diagnostics.'));
        });
        document.getElementById('ops-db-view-data')?.addEventListener('click', () => setDatabaseView('data'));
        document.getElementById('ops-db-view-schema')?.addEventListener('click', () => setDatabaseView('schema'));
        window.addEventListener('resize', scheduleSchemaLineRender);
        void initializeOperationsPage();
    });
})();
