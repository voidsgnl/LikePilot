"""Persistent local secrets used by dashboard authentication."""
import os
import secrets

from likepilot.core.paths import runtime_path

_WEAK_PASSWORDS = {
    "likepilot2026",
    "change-this-password",
    "admin",
    "password",
}
_WEAK_SESSION_KEYS = {
    "replace-with-a-long-random-secret",
    "secret",
    "development",
}


def _read_or_create_secret(filename, size=48):
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
    configured = os.getenv("DASHBOARD_PASS", "").strip()
    if configured and configured.lower() not in _WEAK_PASSWORDS:
        return configured, False
    return _read_or_create_secret("dashboard-password"), True


def resolve_flask_secret_key():
    configured = os.getenv("FLASK_SECRET_KEY", "").strip()
    if configured and configured.lower() not in _WEAK_SESSION_KEYS:
        return configured
    return _read_or_create_secret("dashboard-session.key")
