"""Authenticated encryption for locally persisted LikePilot secrets."""
import os
import threading

from cryptography.fernet import Fernet, InvalidToken

from likepilot.core.paths import runtime_path

_PREFIX = "enc:v1:"
_KEY_ENV = "LIKEPILOT_CREDENTIAL_KEY"
_LOCK = threading.RLock()


class CredentialEncryptionError(RuntimeError):
    """Raised when an encrypted credential cannot be safely recovered."""


def _load_key(create=True):
    with _LOCK:
        configured = os.getenv(_KEY_ENV)
        key_path = runtime_path("credential.key")
        if configured:
            key = configured.encode("ascii")
            try:
                Fernet(key)
            except (ValueError, TypeError) as error:
                raise CredentialEncryptionError("LIKEPILOT_CREDENTIAL_KEY is invalid.") from error
            return key

        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        if os.path.exists(key_path):
            try:
                with open(key_path, "rb") as stream:
                    key = stream.read().strip()
                Fernet(key)
            except (OSError, ValueError, TypeError) as error:
                raise CredentialEncryptionError(
                    "The LikePilot credential key is missing or invalid; refusing to overwrite encrypted credentials."
                ) from error
            try:
                os.chmod(key_path, 0o600)
            except OSError:
                pass
            return key

        if not create:
            raise CredentialEncryptionError(
                "The LikePilot credential key is missing; refusing to generate a replacement for existing encrypted credentials."
            )
        key = Fernet.generate_key()
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        descriptor = os.open(key_path, flags, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(key)
                stream.flush()
                os.fsync(stream.fileno())
        except Exception:
            try:
                os.remove(key_path)
            except OSError:
                pass
            raise
        return key


def is_encrypted(value):
    return isinstance(value, str) and value.startswith(_PREFIX)


def encrypt_secret(value):
    if value is None or value == "":
        return value
    token = Fernet(_load_key()).encrypt(str(value).encode("utf-8")).decode("ascii")
    return _PREFIX + token


def decrypt_secret(value):
    if value is None or value == "":
        return value
    if not is_encrypted(value):
        # Plaintext values are returned only for one-time legacy migration.
        return value
    try:
        token = value[len(_PREFIX):].encode("ascii")
        return Fernet(_load_key(create=False)).decrypt(token).decode("utf-8")
    except (InvalidToken, UnicodeError, ValueError, TypeError) as error:
        raise CredentialEncryptionError(
            "Unable to decrypt a LikePilot credential. Check that the original credential.key is present."
        ) from error
