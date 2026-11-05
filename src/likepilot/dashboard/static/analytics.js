(function () {
    const ctx = document.getElementById('mainEarningsChart').getContext('2d');
    const exportButton = document.getElementById('export-activity-btn');
    const exportStart = document.getElementById('export-start-date');
    const exportEnd = document.getElementById('export-end-date');
    const exportFormat = document.getElementById('export-format');

    function getChartColors() {
        const styles = getComputedStyle(document.documentElement);
        return {
            accent: styles.getPropertyValue('--accent').trim() || '#0f6fff',
            textSoft: styles.getPropertyValue('--text-soft').trim() || '#7f90a8'
        };
    }

    function buildChart() {
        const colors = getChartColors();
        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    borderColor: colors.accent,
                    backgroundColor: 'rgba(111, 218, 122, 0.15)',
                    borderWidth: 3,
                    pointBackgroundColor: colors.accent,
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointHoverBorderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    shadowOffsetX: 0,
                    shadowOffsetY: 4,
                    shadowBlur: 8,
                    shadowColor: 'rgba(111, 218, 122, 0.3)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart'
                },
                layout: {
                    padding: {
                        bottom: 10
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(22, 23, 20, 0.95)',
                        titleColor: colors.accent,
                        bodyColor: '#edf2e8',
                        borderColor: 'rgba(164, 185, 152, 0.3)',
                        borderWidth: 1,
                        cornerRadius: 8,
                        displayColors: false,
                        callbacks: {
                            title: function(context) {
                                return new Date(context[0].parsed.x).toLocaleString();
                            },
                            label: function(context) {
                                return `Credits: ${context.parsed.y}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: colors.textSoft,
                            autoSkip: true,
                            maxRotation: 0
                        },
                        grid: { display: false }
                    },
                    y: {
                        ticks: { color: colors.textSoft },
                        grid: { color: 'rgba(127, 144, 168, 0.16)' }
                    }
                }
            }
        });
    }

    let mainChart = buildChart();

    function refreshChartLayout() {
        if (!mainChart) {
            return;
        }
        requestAnimationFrame(() => {
            mainChart.resize();
            mainChart.update('none');
        });
    }

    function renderStats(data) {
        mainChart.data.labels = data.history.map(h => h.time);
        mainChart.data.datasets[0].data = data.history.map(h => h.credits);
        mainChart.update();

        const metrics = data.metrics || {};
        const gain = metrics.session_gain ?? 0;
        document.getElementById('metric-latest').innerText = metrics.latest_credits ?? 0;
        document.getElementById('metric-gain').innerText = formatSignedNumber(gain);
        document.getElementById('metric-peak').innerText = metrics.session_peak ?? 0;
        document.getElementById('metric-samples').innerText = metrics.samples ?? 0;

        const breakdown = document.getElementById('platform-breakdown');
        const platforms = Object.entries(data.platform_stats || {});
        breakdown.innerHTML = platforms.length
            ? platforms.map(([platform, count]) => `
                <div class="event-item" style="display:flex; justify-content:space-between; gap:12px; align-items:center; padding:12px 14px;">
                    <span style="font-weight:700;">${escapeHtml(platform)}</span>
                    <span class="chip chip-running">${count}</span>
                </div>
            `).join('')
            : `<div class="section-subtle">No samples recorded yet.</div>`;

        const summary = document.getElementById('session-summary');
        const feedback = document.getElementById('analytics-feedback');
        if (!metrics.samples) {
            summary.innerText = 'No credit snapshots are recorded yet. Start an agent and let at least one credit update land.';
        } else {
            summary.innerText = `This session has recorded ${metrics.samples} credit snapshots. The current balance is ${metrics.latest_credits}, the peak observed value is ${metrics.session_peak}, and the net session movement is ${formatSignedNumber(gain)}.`;
        }
        feedback.innerHTML = `<span class="section-subtle">Analytics synced successfully.</span>`;
    }

    function updateStats() {
        fetchJson('/api/stats')
            .then(renderStats)
            .catch(() => {
                setLoadingState(document.getElementById('analytics-feedback'), 'Unable to load analytics right now.');
            });
    }

    function exportActivity() {
        const params = new URLSearchParams();
        if (exportStart.value) {
            params.set('start_date', exportStart.value);
        }
        if (exportEnd.value) {
            params.set('end_date', exportEnd.value);
        }
        params.set('format', exportFormat.value || 'csv');
        window.location.href = `/api/export?${params.toString()}`;
    }

    window.addEventListener('themechange', () => {
        mainChart.destroy();
        mainChart = buildChart();
        updateStats();
    });

    window.addEventListener('tabchange', (event) => {
        const detail = event.detail || {};
        if (detail.target === 'trends') {
            refreshChartLayout();
        }
    });

    exportButton.addEventListener('click', exportActivity);

    createEventStream(
        '/api/stream/stats',
        renderStats,
        () => setLoadingState(document.getElementById('analytics-feedback'), 'Live analytics stream unavailable. Falling back to polling.'),
        5000,
        updateStats
    );

    // Hourly activity is not part of the current stats API. Do not fabricate samples.
    function initializeHeatmap() {
        const heatmapGrid = document.getElementById('activity-heatmap');
        if (!heatmapGrid) return;
        heatmapGrid.replaceChildren();
    }

    // Initialize prediction chart
    function initializePredictionChart() {
        const predictionCtx = document.getElementById('predictionChart');
        if (!predictionCtx) return;

        const ctx = predictionCtx.getContext('2d');
        const colors = getChartColors();

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Now', '6h', '12h', '18h', '24h'],
                datasets: [{
                    label: 'Projected Credits',
                    data: [1250, 1280, 1320, 1350, 1377],
                    borderColor: colors.accent,
                    backgroundColor: 'rgba(111, 218, 122, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: colors.accent,
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 6
                }, {
                    label: 'Historical Average',
                    data: [1200, 1220, 1240, 1260, 1280],
                    borderColor: 'rgba(164, 185, 152, 0.5)',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    fill: false,
                    pointRadius: 0,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 1500,
                    easing: 'easeOutQuart'
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: colors.textSoft,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(22, 23, 20, 0.95)',
                        titleColor: colors.accent,
                        bodyColor: '#edf2e8',
                        borderColor: 'rgba(164, 185, 152, 0.3)',
                        borderWidth: 1,
                        cornerRadius: 8
                    }
                },
                scales: {
                    x: {
                        ticks: { color: colors.textSoft },
                        grid: { color: 'rgba(255,255,255,0.1)' }
                    },
                    y: {
                        beginAtZero: false,
                        ticks: { color: colors.textSoft },
                        grid: { color: 'rgba(255,255,255,0.1)' }
                    }
                }
            }
        });
    }

    // Initialize advanced components
    initializeHeatmap();
    initializePredictionChart();

})();
