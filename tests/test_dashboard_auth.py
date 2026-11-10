import os
import re

import pytest

from likepilot.dashboard import auth


def test_dashboard_password_is_generated_once_and_persisted(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "runtime_path", lambda name: str(tmp_path / name))
    monkeypatch.delenv("DASHBOARD_PASS", raising=False)

    first, generated = auth.resolve_dashboard_password()
    second, generated_again = auth.resolve_dashboard_password()

    assert generated is True
    assert generated_again is True
    assert re.fullmatch(r"[A-Z0-9]{4}", first)
    assert second == first
    assert (tmp_path / "dashboard-password").read_text(encoding="ascii").strip() == first
    assert os.stat(tmp_path / "dashboard-password").st_mode & 0o777 == 0o600


def test_explicit_four_character_password_overrides_generated_secret(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "runtime_path", lambda name: str(tmp_path / name))
    monkeypatch.setenv("DASHBOARD_PASS", "B7Q2")

    password, generated = auth.resolve_dashboard_password()

    assert password == "B7Q2"
    assert generated is False
    assert not (tmp_path / "dashboard-password").exists()


def test_invalid_configured_password_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "runtime_path", lambda name: str(tmp_path / name))
    monkeypatch.setenv("DASHBOARD_PASS", "this-password-is-too-long")

    with pytest.raises(RuntimeError, match="exactly four uppercase letters or digits"):
        auth.resolve_dashboard_password()


def test_legacy_generated_password_is_migrated_to_four_characters(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "runtime_path", lambda name: str(tmp_path / name))
    monkeypatch.delenv("DASHBOARD_PASS", raising=False)
    password_file = tmp_path / "dashboard-password"
    password_file.write_text("old-long-generated-password", encoding="ascii")

    password, generated = auth.resolve_dashboard_password()

    assert generated is True
    assert re.fullmatch(r"[A-Z0-9]{4}", password)
    assert password_file.read_text(encoding="ascii").strip() == password
    assert os.stat(password_file).st_mode & 0o777 == 0o600


def test_flask_secret_key_is_persistent_and_ignores_placeholder(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "runtime_path", lambda name: str(tmp_path / name))
    monkeypatch.setenv("FLASK_SECRET_KEY", "replace-with-a-long-random-secret")

    first = auth.resolve_flask_secret_key()
    second = auth.resolve_flask_secret_key()

    assert first == second
    assert len(first) >= 40
    assert (tmp_path / "dashboard-session.key").exists()
