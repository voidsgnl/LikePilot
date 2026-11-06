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


def sanitize_diagnostic_html(value):
    """Remove sensitive form and CSRF values from captured page markup."""
    html = redact_sensitive_text(value)
    sensitive_names = re.compile(r"(?i)(password|passwd|token|secret|api[_-]?key|authorization|csrf|auth)")
    input_pattern = re.compile(r"<input\\b[^>]*>", re.IGNORECASE)
    textarea_pattern = re.compile(
        r"(<textarea\\b[^>]*(?:name|id)\\s*=\\s*[\"'][^\"']*(?:password|passwd|token|secret|api[_-]?key|authorization|csrf|auth)[^\"']*[\"'][^>]*>).*?(</textarea\\s*>)",
        re.IGNORECASE | re.DOTALL,
    )
    meta_pattern = re.compile(
        r"(<meta\\b[^>]*(?:name|property)\\s*=\\s*[\"'][^\"']*(?:token|csrf|auth|secret)[^\"']*[\"'][^>]*>)",
        re.IGNORECASE,
    )

    def mask_input(match):
        tag = match.group(0)
        attrs = {
            key.lower(): (quoted or unquoted or "")
            for key, quoted, unquoted in re.findall(
                r"([\\w:-]+)\\s*=\\s*(?:[\"']([^\"']*)[\"']|([^\\s>]+))",
                tag,
            )
        }
        if attrs.get("type", "").lower() in {"password", "hidden"} or any(
            sensitive_names.search(attrs.get(key, "")) for key in ("name", "id", "autocomplete")
        ):
            tag = re.sub(
                r"\\svalue\\s*=\\s*(?:\"[^\"]*\"|'[^']*'|[^\\s>]+)",
                ' value="[REDACTED]"',
                tag,
                flags=re.IGNORECASE,
            )
        return tag

    html = input_pattern.sub(mask_input, html)
    html = textarea_pattern.sub(r"\\1[REDACTED]\\2", html)
    html = meta_pattern.sub(
        lambda match: re.sub(
            r"\\scontent\\s*=\\s*(?:\"[^\"]*\"|'[^']*'|[^\\s>]+)",
            ' content="[REDACTED]"',
            match.group(0),
            flags=re.IGNORECASE,
        ),
        html,
    )
    return html
