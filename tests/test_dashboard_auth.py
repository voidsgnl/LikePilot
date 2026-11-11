import pytest

from likepilot.dashboard import auth


def test_dashboard_password_requires_explicit_configuration(monkeypatch):
    monkeypatch.delenv("DASHBOARD_PASS", raising=False)

    with pytest.raises(RuntimeError, match="DASHBOARD_PASS is required"):
        auth.resolve_dashboard_password()


@pytest.mark.parametrize("value", ["0", "7", "0427", "1234567890", "9" * 64])
def test_numeric_password_of_supported_length_is_accepted(monkeypatch, value):
    monkeypatch.setenv("DASHBOARD_PASS", value)

    assert auth.resolve_dashboard_password() == value


@pytest.mark.parametrize("value", ["", "admin", "abcd", "A7K2", "9" * 65, " 1234", "１２３４"])
def test_invalid_configured_password_is_rejected(monkeypatch, value):
    monkeypatch.setenv("DASHBOARD_PASS", value)

    with pytest.raises(RuntimeError, match="between 1 and 64 digits"):
        auth.resolve_dashboard_password()


def test_flask_secret_key_is_persistent_and_ignores_placeholder(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "runtime_path", lambda name: str(tmp_path / name))
    monkeypatch.setenv("FLASK_SECRET_KEY", "replace-with-a-long-random-secret")

    first = auth.resolve_flask_secret_key()
    second = auth.resolve_flask_secret_key()

    assert first == second
    assert len(first) >= 40
    assert (tmp_path / "dashboard-session.key").exists()
