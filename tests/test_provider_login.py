from likepilot.core import credentials, state


def _use_temporary_database(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "DB_FILE", str(tmp_path / "likepilot.db"))
    monkeypatch.setattr(state, "LEGACY_DB_FILE", str(tmp_path / "likeit.db"))
    monkeypatch.setattr(state, "AGENTS_FILE", str(tmp_path / "agents.json"))
    monkeypatch.setattr(state, "LEGACY_STATS_FILE", str(tmp_path / "stats.json"))
    monkeypatch.setattr(credentials, "runtime_path", lambda name: str(tmp_path / name))


def test_provider_login_settings_are_isolated_by_provider(tmp_path, monkeypatch):
    _use_temporary_database(tmp_path, monkeypatch)

    state.set_provider_login_settings("Like4Like", True, "l4l-user", "l4l-secret")
    state.set_provider_login_settings("KingdomLikes", False, "kl-user", "kl-secret")

    like4like = state.get_provider_login_settings("Like4Like")
    kingdomlikes = state.get_provider_login_settings("KingdomLikes")
    youlikehits = state.get_provider_login_settings("YouLikeHits")

    assert like4like == {
        "enabled": True,
        "username": "l4l-user",
        "password": "l4l-secret",
    }
    assert kingdomlikes == {
        "enabled": False,
        "username": "kl-user",
        "password": "kl-secret",
    }
    assert youlikehits == {
        "enabled": False,
        "username": "",
        "password": "",
    }


def test_provider_login_password_is_preserved_when_password_field_is_blank(tmp_path, monkeypatch):
    _use_temporary_database(tmp_path, monkeypatch)

    state.set_provider_login_settings("Like4Like", True, "old-user", "saved-secret")
    state.set_provider_login_settings("Like4Like", False, "new-user")

    settings = state.get_provider_login_settings("Like4Like")
    assert settings["enabled"] is False
    assert settings["username"] == "new-user"
    assert settings["password"] == "saved-secret"


def test_provider_login_password_can_be_cleared(tmp_path, monkeypatch):
    _use_temporary_database(tmp_path, monkeypatch)

    state.set_provider_login_settings("YouLikeHits", True, "user", "secret")
    state.set_provider_login_settings("YouLikeHits", False, "user", clear_password=True)

    settings = state.get_provider_login_settings("YouLikeHits")
    assert settings["enabled"] is False
    assert settings["password"] == ""


def test_provider_login_rejects_unknown_provider():
    import pytest

    with pytest.raises(ValueError, match="Unsupported provider"):
        state.get_provider_login_settings("Unknown")



def test_provider_password_is_encrypted_at_rest_and_decrypted_for_runtime(tmp_path, monkeypatch):
    import sqlite3

    _use_temporary_database(tmp_path, monkeypatch)
    state.set_provider_login_settings("Like4Like", True, "operator", "private-password")

    with sqlite3.connect(state.DB_FILE) as conn:
        stored = conn.execute(
            "SELECT value FROM settings WHERE key = 'provider_login.Like4Like.password'"
        ).fetchone()[0]
    assert stored.startswith("enc:v1:")
    assert "private-password" not in stored
    assert state.get_provider_login_settings("Like4Like")["password"] == "private-password"


def test_legacy_plaintext_provider_password_is_migrated(tmp_path, monkeypatch):
    import sqlite3

    _use_temporary_database(tmp_path, monkeypatch)
    state.init_db()
    with sqlite3.connect(state.DB_FILE) as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            ("provider_login.KingdomLikes.password", "legacy-password"),
        )

    state.init_db()
    with sqlite3.connect(state.DB_FILE) as conn:
        stored = conn.execute(
            "SELECT value FROM settings WHERE key = 'provider_login.KingdomLikes.password'"
        ).fetchone()[0]
    assert stored.startswith("enc:v1:")
    assert state.get_provider_login_settings("KingdomLikes")["password"] == "legacy-password"


def test_agent_password_is_encrypted_and_not_exposed_by_general_agent_read(tmp_path, monkeypatch):
    import sqlite3

    _use_temporary_database(tmp_path, monkeypatch)
    state.add_agent("secure-agent", "Default", login_user="legacy-user", login_password="agent-secret")

    with sqlite3.connect(state.DB_FILE) as conn:
        stored = conn.execute(
            "SELECT login_password FROM agents WHERE name = 'secure-agent'"
        ).fetchone()[0]
    assert stored.startswith("enc:v1:")
    assert "agent-secret" not in stored
    assert "login_password" not in state.get_agent("secure-agent")


def test_generic_secret_storage_encrypts_and_round_trips(tmp_path, monkeypatch):
    import sqlite3

    _use_temporary_database(tmp_path, monkeypatch)
    state.set_secret("captcha.api_key", "captcha-secret")
    assert state.get_secret("captcha.api_key") == "captcha-secret"
    with sqlite3.connect(state.DB_FILE) as conn:
        stored = conn.execute(
            "SELECT value FROM settings WHERE key = 'secret.captcha.api_key'"
        ).fetchone()[0]
    assert stored.startswith("enc:v1:")
    assert "captcha-secret" not in stored



def test_decrypt_does_not_generate_replacement_when_key_is_missing(tmp_path, monkeypatch):
    import pytest
    from likepilot.core.credentials import CredentialEncryptionError, decrypt_secret

    monkeypatch.setattr(credentials, "runtime_path", lambda name: str(tmp_path / name))
    with pytest.raises(CredentialEncryptionError, match="key is missing"):
        decrypt_secret("enc:v1:unreadable-token")
    assert not (tmp_path / "credential.key").exists()



def test_user_secret_with_encryption_prefix_is_still_encrypted(tmp_path, monkeypatch):
    import sqlite3

    _use_temporary_database(tmp_path, monkeypatch)
    literal = "enc:v1:this-is-the-user-password"
    state.set_provider_login_settings("Like4Like", True, "operator", literal)
    with sqlite3.connect(state.DB_FILE) as conn:
        stored = conn.execute(
            "SELECT value FROM settings WHERE key = 'provider_login.Like4Like.password'"
        ).fetchone()[0]
    assert stored != literal
    assert stored.startswith("enc:v1:")
    assert state.get_provider_login_settings("Like4Like")["password"] == literal
