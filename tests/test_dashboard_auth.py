import os

from likepilot.dashboard import auth


def test_dashboard_password_is_generated_once_and_persisted(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "runtime_path", lambda name: str(tmp_path / name))
    monkeypatch.delenv("DASHBOARD_PASS", raising=False)

    first, generated = auth.resolve_dashboard_password()
    second, generated_again = auth.resolve_dashboard_password()

    assert generated is True
    assert generated_again is True
    assert len(first) >= 40
    assert second == first
    assert (tmp_path / "dashboard-password").read_text(encoding="ascii").strip() == first
    assert os.stat(tmp_path / "dashboard-password").st_mode & 0o777 == 0o600


def test_explicit_dashboard_password_overrides_generated_secret(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "runtime_path", lambda name: str(tmp_path / name))
    monkeypatch.setenv("DASHBOARD_PASS", "a-strong-user-configured-password")

    password, generated = auth.resolve_dashboard_password()

    assert password == "a-strong-user-configured-password"
    assert generated is False
    assert not (tmp_path / "dashboard-password").exists()


def test_weak_dashboard_password_is_replaced_by_generated_secret(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "runtime_path", lambda name: str(tmp_path / name))
    monkeypatch.setenv("DASHBOARD_PASS", "likepilot2026")

    password, generated = auth.resolve_dashboard_password()

    assert generated is True
    assert password != "likepilot2026"


def test_flask_secret_key_is_persistent_and_ignores_placeholder(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "runtime_path", lambda name: str(tmp_path / name))
    monkeypatch.setenv("FLASK_SECRET_KEY", "replace-with-a-long-random-secret")

    first = auth.resolve_flask_secret_key()
    second = auth.resolve_flask_secret_key()

    assert first == second
    assert len(first) >= 40
    assert (tmp_path / "dashboard-session.key").exists()
