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
