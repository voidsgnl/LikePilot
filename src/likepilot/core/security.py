"""Redaction helpers for secrets in application logs and diagnostics."""
import re
import threading

_LOCK = threading.RLock()
_REGISTERED_SECRETS = set()

_PATTERNS = (
    (re.compile(r"(?i)(https?://)[^/@:\s]+:[^/@\s]+@"), r"\1[REDACTED]@"),
    (re.compile(r"(?i)(https?://(?:discord(?:app)?\.com)/api/webhooks/)\d+/[A-Za-z0-9._-]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)([?&](?:password|passwd|token|api[_-]?key|secret|authorization|access[_-]?token|client[_-]?secret)=)[^&#\s]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(\b(?:authorization\s*:\s*basic)\s+)[A-Za-z0-9+/=]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(\bbearer\s+)[A-Za-z0-9._~+/-]+=*"), r"\1[REDACTED]"),
    (re.compile(r"\b\d{5,}:[A-Za-z0-9_-]{20,}\b"), "[REDACTED_TELEGRAM_TOKEN]"),
    (re.compile(r"(?i)(\b(?:password|passwd|token|api[_-]?key|secret|webhook)\b\s*[:=]\s*[\"']?)[^,\s\"'&]+"), r"\1[REDACTED]"),
)


def register_secret(value):
    """Register a runtime secret so exact occurrences can be scrubbed."""
    if not isinstance(value, str) or len(value) < 4:
        return
    with _LOCK:
        _REGISTERED_SECRETS.add(value)


def redact_sensitive_text(value):
    """Remove known secret values and common credential-bearing patterns."""
    text = str(value)
    with _LOCK:
        secrets = sorted(_REGISTERED_SECRETS, key=len, reverse=True)
    for secret in secrets:
        text = text.replace(secret, "[REDACTED]")
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text
