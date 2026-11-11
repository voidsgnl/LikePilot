"""Dashboard credential validation and persistent Flask session secrets."""
import os
import re
import secrets

from likepilot.core.paths import runtime_path

_VAULT_PASSWORD_PATTERN = re.compile(r"^[0-9]{1,64}$")
_WEAK_SESSION_KEYS = {
    "replace-with-a-long-random-secret",
    "secret",
    "development",
}


def _read_or_create_secret(filename, size=48):
    """Read or create a persistent high-entropy secret, such as Flask's key."""
    path = runtime_path(filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="ascii") as stream:
                value = stream.read().strip()
            if not value:
                raise RuntimeError(f"Dashboard secret file is empty: {path}")
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
            return value
        except OSError as error:
            raise RuntimeError(f"Unable to read dashboard secret file: {path}") from error

    value = secrets.token_urlsafe(size)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        with open(path, "r", encoding="ascii") as stream:
            existing = stream.read().strip()
        if not existing:
            raise RuntimeError(f"Dashboard secret file is empty: {path}")
        return existing
    try:
        with os.fdopen(descriptor, "w", encoding="ascii") as stream:
            stream.write(value + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        try:
            os.remove(path)
        except OSError:
            pass
        raise
    return value


def resolve_dashboard_password():
    """Return the explicitly configured 1–64 digit local vault password."""
    configured = os.getenv("DASHBOARD_PASS", "")
    if not configured:
        raise RuntimeError(
            "DASHBOARD_PASS is required. Set it in data/config/.env to "
            "between 1 and 64 digits (0-9)."
        )
    if not _VAULT_PASSWORD_PATTERN.fullmatch(configured):
        raise RuntimeError(
            "DASHBOARD_PASS must contain between 1 and 64 digits (0-9)."
        )
    return configured


def resolve_flask_secret_key():
    configured = os.getenv("FLASK_SECRET_KEY", "").strip()
    if configured and configured.lower() not in _WEAK_SESSION_KEYS:
        return configured
    return _read_or_create_secret("dashboard-session.key")
