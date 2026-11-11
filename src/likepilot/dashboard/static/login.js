/* Single rotating numeric dial for the local vault login. */
(function () {
    'use strict';

    const digits = '0123456789';
    const dial = document.getElementById('vault-dial');
    const numberTrack = document.getElementById('dial-number-track');
    const digitLabels = Array.from(document.querySelectorAll('.dial-digit'));
    const currentDisplay = document.getElementById('dial-current');
    const confirmButton = document.getElementById('confirm-digit');
    const removeButton = document.getElementById('remove-digit');
    const clearButton = document.getElementById('clear-combination');
    const passwordField = document.getElementById('vault-password');
    const codeDisplay = document.getElementById('combination-code');
    const countDisplay = document.getElementById('combination-count');
    const submitHint = document.getElementById('vault-submit-hint');
    const form = document.getElementById('vault-form');
    const darkButton = document.getElementById('theme-dark');
    const lightButton = document.getElementById('theme-light');
    const root = document.documentElement;
    const selection = [];

    let selectedIndex = 0;
    let rotation = 0;
    let dragging = false;
    let pointerAngle = 0;
    let startRotation = 0;

    const modulo = (value, divisor) => ((value % divisor) + divisor) % divisor;

    function pointerAngleAt(event) {
        const rect = dial.getBoundingClientRect();
        const x = event.clientX - rect.left - rect.width / 2;
        const y = event.clientY - rect.top - rect.height / 2;
        return Math.atan2(y, x) * 180 / Math.PI;
    }

    function renderDial() {
        rotation = -selectedIndex * 36;
        numberTrack.style.transform = 'rotate(' + rotation + 'deg)';
        digitLabels.forEach(label => {
            const digitIndex = Number(label.dataset.digit);
            const angle = (digitIndex / digits.length) * Math.PI * 2 - Math.PI / 2;
            label.style.left = (50 + Math.cos(angle) * 42) + '%';
            label.style.top = (50 + Math.sin(angle) * 42) + '%';
            label.style.transform = 'translate(-50%, -50%) rotate(' + (-rotation) + 'deg)';
            label.classList.toggle('is-current', digitIndex === selectedIndex);
        });
        const digit = digits[selectedIndex];
        currentDisplay.textContent = digit;
        confirmButton.setAttribute('aria-label', 'Confirm selected digit ' + digit);
        dial.setAttribute('aria-valuenow', digit);
        dial.setAttribute('aria-valuetext', digit + ' selected');
    }

    function setSelectedIndex(index) {
        selectedIndex = modulo(index, digits.length);
        renderDial();
    }

    function updateCombination() {
        const value = selection.join('');
        passwordField.value = value;
        passwordField.maxLength = 64;
        countDisplay.textContent = selection.length + ' / 64';
        removeButton.disabled = selection.length === 0;
        clearButton.disabled = selection.length === 0;
        codeDisplay.replaceChildren();

        if (!selection.length) {
            const empty = document.createElement('span');
            empty.className = 'combination-empty';
            empty.textContent = 'Your digits will appear here';
            codeDisplay.appendChild(empty);
        } else {
            selection.forEach((digit, index) => {
                const slot = document.createElement('span');
                slot.className = 'combination-slot';
                slot.textContent = digit;
                slot.setAttribute('aria-label', 'Digit ' + (index + 1) + ': ' + digit);
                codeDisplay.appendChild(slot);
            });
        }

        submitHint.textContent = selection.length
            ? selection.length + ' digit' + (selection.length === 1 ? '' : 's') + ' selected.'
            : 'Add at least one digit to continue.';
    }

    function confirmDigit() {
        if (selection.length >= 64) {
            submitHint.textContent = 'The maximum password length is 64 digits.';
            return;
        }
        selection.push(digits[selectedIndex]);
        updateCombination();
        setSelectedIndex(0);
    }

    function removeLastDigit() {
        selection.pop();
        updateCombination();
    }

    function beginRotation(event) {
        if (event.target.closest('#confirm-digit')) return;
        event.preventDefault();
        dragging = true;
        pointerAngle = pointerAngleAt(event);
        startRotation = rotation;
        dial.setPointerCapture(event.pointerId);
        dial.classList.add('is-dragging');
    }

    function rotateWithPointer(event) {
        if (!dragging) return;
        const nextAngle = pointerAngleAt(event);
        let delta = nextAngle - pointerAngle;
        if (delta > 180) delta -= 360;
        if (delta < -180) delta += 360;
        rotation = startRotation + delta;
        setSelectedIndex(Math.round(-rotation / 36));
    }

    function endRotation(event) {
        if (!dragging) return;
        dragging = false;
        dial.classList.remove('is-dragging');
        if (dial.hasPointerCapture(event.pointerId)) dial.releasePointerCapture(event.pointerId);
    }

    dial.addEventListener('pointerdown', beginRotation);
    dial.addEventListener('pointermove', rotateWithPointer);
    dial.addEventListener('pointerup', endRotation);
    dial.addEventListener('pointercancel', endRotation);
    dial.addEventListener('lostpointercapture', () => {
        dragging = false;
        dial.classList.remove('is-dragging');
    });
    dial.addEventListener('wheel', event => {
        event.preventDefault();
        setSelectedIndex(selectedIndex + (event.deltaY > 0 ? 1 : -1));
    }, { passive: false });

    dial.addEventListener('keydown', event => {
        if (event.key === 'ArrowRight' || event.key === 'ArrowUp') {
            event.preventDefault();
            setSelectedIndex(selectedIndex + 1);
        } else if (event.key === 'ArrowLeft' || event.key === 'ArrowDown') {
            event.preventDefault();
            setSelectedIndex(selectedIndex - 1);
        } else if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            confirmDigit();
        }
    });

    confirmButton.addEventListener('click', confirmDigit);
    removeButton.addEventListener('click', removeLastDigit);
    clearButton.addEventListener('click', () => {
        selection.length = 0;
        updateCombination();
        setSelectedIndex(0);
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
        if (!selection.length) {
            event.preventDefault();
            submitHint.textContent = 'Add at least one digit before unlocking.';
            dial.focus();
            return;
        }
        passwordField.value = selection.join('');
    });

    renderDial();
    updateCombination();
})();
