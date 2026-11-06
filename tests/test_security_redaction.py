from likepilot.core.security import redact_sensitive_text, register_secret


def test_redactor_removes_registered_secret_values():
    register_secret("runtime-secret-value")
    assert "runtime-secret-value" not in redact_sensitive_text("Failure: runtime-secret-value")


def test_redactor_removes_common_credential_patterns():
    raw = (
        "proxy=https://operator:proxy-pass@127.0.0.1:8080 "
        "request?api_key=api-secret "
        "Authorization: Bearer abc.def.ghi "
        "https://discord.com/api/webhooks/123456/discord-token "
        "bot 123456:abcdefghijklmnopqrstuvwxyzABCDE"
    )
    safe = redact_sensitive_text(raw)
    for secret in ("operator:proxy-pass", "api-secret", "abc.def.ghi", "discord-token", "abcdefghijklmnopqrstuvwxyzABCDE"):
        assert secret not in safe


def test_agent_logs_are_redacted_before_persistence(tmp_path, monkeypatch):
    from likepilot.core import credentials, state

    monkeypatch.setattr(state, "DB_FILE", str(tmp_path / "likepilot.db"))
    monkeypatch.setattr(state, "LEGACY_DB_FILE", str(tmp_path / "likeit.db"))
    monkeypatch.setattr(state, "AGENTS_FILE", str(tmp_path / "agents.json"))
    monkeypatch.setattr(state, "LEGACY_STATS_FILE", str(tmp_path / "stats.json"))
    monkeypatch.setattr(credentials, "runtime_path", lambda name: str(tmp_path / name))
    register_secret("registered-private-value")

    state.append_agent_log(
        "redaction-agent",
        "Failure: registered-private-value at https://operator:proxy-pass@127.0.0.1:8080",
    )
    entries = state.list_agent_logs("redaction-agent", limit=1)
    assert "registered-private-value" not in entries[0]
    assert "operator:proxy-pass" not in entries[0]
    assert "[REDACTED]" in entries[0]


def test_notifications_redact_sensitive_error_details(monkeypatch):
    from likepilot.core.notifications import NotificationManager

    manager = NotificationManager()
    manager.enabled = True
    manager.notify_on = {"agent_crashed": True}
    sent = []
    monkeypatch.setattr(manager, "_send_telegram", lambda message, **kwargs: sent.append(message) or True)
    manager.telegram_bot_token = "123456:abcdefghijklmnopqrstuvwxyzABCDE"
    manager.telegram_chat_id = "chat"
    manager.notify("agent_crashed", "Agent failed with https://user:proxy-pass@host:8080")

    assert sent
    assert "user:proxy-pass" not in sent[0]
