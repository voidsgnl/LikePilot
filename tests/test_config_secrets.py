import json

from likepilot.core import config, credentials, state


def _use_temporary_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_FILE", str(tmp_path / "config.json"))
    monkeypatch.setattr(state, "DB_FILE", str(tmp_path / "likepilot.db"))
    monkeypatch.setattr(state, "LEGACY_DB_FILE", str(tmp_path / "likeit.db"))
    monkeypatch.setattr(state, "AGENTS_FILE", str(tmp_path / "agents.json"))
    monkeypatch.setattr(state, "LEGACY_STATS_FILE", str(tmp_path / "stats.json"))
    monkeypatch.setattr(credentials, "runtime_path", lambda name: str(tmp_path / name))


def _write_config(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def _read_config(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_authenticated_proxy_entries_migrate_to_encrypted_storage(tmp_path, monkeypatch):
    _use_temporary_storage(tmp_path, monkeypatch)
    config_path = tmp_path / "config.json"
    proxies = ["http://operator:proxy-secret@127.0.0.1:8080"]
    _write_config(config_path, {"proxy": {"proxy_list": proxies}})

    assert config.get_proxy_list() == proxies
    assert _read_config(config_path)["proxy"]["proxy_list"] == []
    stored = state.get_secret("config.proxy.proxy_list")
    assert stored.startswith("[")
    assert "proxy-secret" not in stored
    assert config.get_proxy_list() == proxies


def test_proxy_updates_stay_in_encrypted_storage(tmp_path, monkeypatch):
    _use_temporary_storage(tmp_path, monkeypatch)
    config_path = tmp_path / "config.json"
    _write_config(config_path, {"proxy": {"proxy_list": []}})

    assert config.add_proxy("http://user:secret@localhost:8080") is True
    assert config.add_proxy("http://user:secret@localhost:8080") is False
    assert config.remove_proxy("http://user:secret@localhost:8080") is True
    assert config.get_proxy_list() == []
    assert "secret" not in config_path.read_text(encoding="utf-8")


def test_notification_tokens_migrate_and_clear_legacy_config(tmp_path, monkeypatch):
    _use_temporary_storage(tmp_path, monkeypatch)
    config_path = tmp_path / "config.json"
    _write_config(config_path, {
        "notifications": {
            "discord_webhook": "https://discord.example/webhook-secret",
            "telegram_bot_token": "123456:telegram-secret",
        }
    })

    assert config.get_notification_secret("discord_webhook") == "https://discord.example/webhook-secret"
    assert config.get_notification_secret("telegram_bot_token") == "123456:telegram-secret"
    saved = _read_config(config_path)["notifications"]
    assert saved["discord_webhook"] == ""
    assert saved["telegram_bot_token"] == ""
    assert state.get_secret("config.notifications.discord_webhook").startswith("enc:v1:")
    assert state.get_secret("config.notifications.telegram_bot_token").startswith("enc:v1:")
    raw = config_path.read_text(encoding="utf-8")
    assert "webhook-secret" not in raw
    assert "telegram-secret" not in raw


def test_notification_secret_rejects_unknown_name():
    import pytest

    with pytest.raises(ValueError, match="Unsupported notification secret"):
        config.get_notification_secret("email_password")
