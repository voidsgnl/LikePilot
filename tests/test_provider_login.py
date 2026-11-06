from likepilot.core import state


def _use_temporary_database(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "DB_FILE", str(tmp_path / "likepilot.db"))
    monkeypatch.setattr(state, "LEGACY_DB_FILE", str(tmp_path / "likeit.db"))
    monkeypatch.setattr(state, "AGENTS_FILE", str(tmp_path / "agents.json"))
    monkeypatch.setattr(state, "LEGACY_STATS_FILE", str(tmp_path / "stats.json"))


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
