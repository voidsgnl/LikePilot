/* Four-ring local vault login. The server remains the source of truth. */
(function () {
    'use strict';

    const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    const rings = Array.from(document.querySelectorAll('.character-ring'));
    const passwordField = document.getElementById('vault-password');
    const codeDisplay = document.getElementById('combination-code');
    const form = document.getElementById('vault-form');
    const darkButton = document.getElementById('theme-dark');
    const lightButton = document.getElementById('theme-light');
    const root = document.documentElement;
    const selection = ['A', 'A', 'A', 'A'];

    function updateCombination() {
        const code = selection.join('');
        passwordField.value = code;
        codeDisplay.replaceChildren(...selection.map(character => {
            const slot = document.createElement('span');
            slot.textContent = character;
            return slot;
        }));
    }

    function chooseCharacter(ringIndex, character, selectedButton) {
        selection[ringIndex] = character;
        rings[ringIndex].querySelectorAll('.wheel-char').forEach(button => {
            const selected = button === selectedButton;
            button.classList.toggle('selected', selected);
            button.setAttribute('aria-pressed', String(selected));
        });
        updateCombination();
    }

    rings.forEach((ring, ringIndex) => {
        alphabet.split('').forEach((character, characterIndex) => {
            const angle = (characterIndex / alphabet.length) * Math.PI * 2 - Math.PI / 2;
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'wheel-char';
            button.textContent = character;
            button.style.setProperty('--char-x', (50 + Math.cos(angle) * 50) + '%');
            button.style.setProperty('--char-y', (50 + Math.sin(angle) * 50) + '%');
            button.setAttribute('aria-label', 'Ring ' + (ringIndex + 1) + ', character ' + character);
            button.setAttribute('aria-pressed', String(character === 'A'));
            if (character === 'A') button.classList.add('selected');
            button.addEventListener('click', () => chooseCharacter(ringIndex, character, button));
            ring.appendChild(button);
        });
    });

    function applyTheme(theme) {
        const next = theme === 'light' ? 'light' : 'dark';
        root.dataset.theme = next;
        try { localStorage.setItem('theme', next); } catch (_) {}
        darkButton.classList.toggle('active', next === 'dark');
        lightButton.classList.toggle('active', next === 'light');
        darkButton.setAttribute('aria-pressed', String(next === 'dark'));
        lightButton.setAttribute('aria-pressed', String(next === 'light'));
        document.querySelector('meta[name="theme-color"]')
            .setAttribute('content', next === 'dark' ? '#080d16' : '#edf2f4');
    }

    darkButton.addEventListener('click', () => applyTheme('dark'));
    lightButton.addEventListener('click', () => applyTheme('light'));

    let savedTheme = 'dark';
    try {
        const storedTheme = localStorage.getItem('theme');
        if (storedTheme === 'dark' || storedTheme === 'light') savedTheme = storedTheme;
    } catch (_) {}
    applyTheme(savedTheme);

    form.addEventListener('submit', event => {
        if (!form.reportValidity()) {
            event.preventDefault();
            return;
        }
        passwordField.value = selection.join('');
    });

    updateCombination();
})();
