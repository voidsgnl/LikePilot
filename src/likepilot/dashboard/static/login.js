/* ============================================================================
   LOGIN — the standalone sign-in page. Two jobs only:
   1. Password reveal toggle.
   2. Theme switch (mirrors orbit.js, persists to localStorage 'theme').
   ============================================================================ */

(function () {
    'use strict';

    const root  = document.documentElement;
    const input = document.getElementById('password');
    const toggle = document.getElementById('password-toggle');
    const btnDark  = document.getElementById('auth-theme-dark');
    const btnLight = document.getElementById('auth-theme-light');

    /* ---------- password reveal ---------- */
    if (input && toggle) {
        toggle.addEventListener('click', () => {
            const reveal = input.type === 'password';
            input.type = reveal ? 'text' : 'password';
            toggle.textContent = reveal ? 'Hide' : 'Show';
            toggle.setAttribute('aria-label', reveal ? 'Hide password' : 'Show password');
            toggle.setAttribute('aria-pressed', String(reveal));
        });
    }

    /* ---------- theme switch ---------- */
    function applyTheme(theme) {
        const next = theme === 'light' ? 'light' : 'dark';
        root.setAttribute('data-theme', next);
        try { localStorage.setItem('theme', next); } catch (_) {}

        if (btnDark) {
            btnDark.classList.toggle('active', next === 'dark');
            btnDark.setAttribute('aria-pressed', String(next === 'dark'));
        }
        if (btnLight) {
            btnLight.classList.toggle('active', next === 'light');
            btnLight.setAttribute('aria-pressed', String(next === 'light'));
        }

        const meta = document.querySelector('meta[name="theme-color"]');
        if (meta) {
            meta.setAttribute('content', next === 'dark' ? '#070a12' : '#f4f6fb');
        }
    }

    if (btnDark)  btnDark.addEventListener('click',  () => applyTheme('dark'));
    if (btnLight) btnLight.addEventListener('click', () => applyTheme('light'));

    /* ---------- restore saved theme ---------- */
    let saved = 'dark';
    try {
        const stored = localStorage.getItem('theme');
        if (stored === 'light' || stored === 'dark') saved = stored;
    } catch (_) {}
    applyTheme(saved);
})();