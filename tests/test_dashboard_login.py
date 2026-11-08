import importlib


def test_dashboard_login_uses_configured_password_and_throttles_failures(tmp_path, monkeypatch):
    monkeypatch.setenv("LIKEPILOT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DASHBOARD_PASS", "test-strong-dashboard-password")
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-session-signing-secret")
    monkeypatch.setenv("DASHBOARD_USER", "operator")

    module = importlib.import_module("likepilot.dashboard.app")
    module._LOGIN_FAILURES.clear()
    client = module.app.test_client()

    assert module.DASHBOARD_PASS == "test-strong-dashboard-password"
    assert module.app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert module.app.config["SESSION_COOKIE_SAMESITE"] == "Lax"

    login_page = client.get("/login")
    assert login_page.status_code == 200
    assert b"Your agents." in login_page.data
    assert b"Enter workspace" in login_page.data
    assert b"pilot-flight.svg" in login_page.data
    assert b'name="username"' in login_page.data
    assert b'name="password"' in login_page.data

    for _ in range(module._LOGIN_FAILURE_LIMIT):
        response = client.post(
            "/login",
            data={"username": "operator", "password": "wrong-password"},
        )
        assert response.status_code == 200

    blocked = client.post(
        "/login",
        data={"username": "operator", "password": "test-strong-dashboard-password"},
    )
    assert blocked.status_code == 200
    assert b"Please wait a few minutes" in blocked.data
    assert b"TOO_MANY_ATTEMPTS" not in blocked.data
    module._LOGIN_FAILURES.clear()
