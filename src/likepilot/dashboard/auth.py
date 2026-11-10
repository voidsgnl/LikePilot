"""Local dashboard credentials used by the four-ring vault login."""
import os
import re
import secrets

from likepilot.core.paths import runtime_path

_VAULT_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
_VAULT_PASSWORD_PATTERN = re.compile(r"^[A-Z0-9]{4}$")
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


def _new_vault_password():
    """Generate four cryptographically random characters for the local vault."""
    return "".join(secrets.choice(_VAULT_ALPHABET) for _ in range(4))


def _write_vault_password(path, value):
    """Persist the local vault password with owner-only filesystem permissions."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="ascii") as stream:
            stream.write(value + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def resolve_dashboard_password():
    """Resolve the four-character vault password from env or local runtime data.

    Older installations may have a longer generated password file. It is
    replaced once with a new four-character value so the vault can be used.
    """
    configured = os.getenv("DASHBOARD_PASS", "").strip()
    if configured:
        if not _VAULT_PASSWORD_PATTERN.fullmatch(configured):
            raise RuntimeError(
                "DASHBOARD_PASS must contain exactly four uppercase letters or digits (A-Z, 0-9)."
            )
        return configured, False

    path = runtime_path("dashboard-password")
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="ascii") as stream:
                existing = stream.read().strip()
        except OSError as error:
            raise RuntimeError(f"Unable to read dashboard password file: {path}") from error
        if _VAULT_PASSWORD_PATTERN.fullmatch(existing):
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
            return existing, True

    password = _new_vault_password()
    _write_vault_password(path, password)
    return password, True


def resolve_flask_secret_key():
    configured = os.getenv("FLASK_SECRET_KEY", "").strip()
    if configured and configured.lower() not in _WEAK_SESSION_KEYS:
        return configured
    return _read_or_create_secret("dashboard-session.key")
