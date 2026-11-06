import importlib


def _dashboard_client():
    module = importlib.import_module("likepilot.dashboard.app")
    client = module.app.test_client()
    with client.session_transaction() as session:
        session["logged_in"] = True
    return module, client


def test_agent_create_endpoint_validates_and_persists(monkeypatch):
    module, client = _dashboard_client()
    created = []
    monkeypatch.setattr(module, "add_agent", lambda *args, **kwargs: created.append((args, kwargs)))

    invalid = client.post("/api/agents/add", json={"name": "worker"})
    assert invalid.status_code == 400

    response = client.post(
        "/api/agents/add",
        json={"name": "worker", "profile": "profile-a", "site": "Like4Like"},
    )
    assert response.status_code == 200
    assert created == [(("worker", "profile-a"), {
        "proxy": None,
        "site": "Like4Like",
        "fallback_platform": None,
        "fallback_chain": None,
        "comment_templates": None,
    })]


def test_agent_configuration_endpoint_updates_stopped_agent(monkeypatch):
    module, client = _dashboard_client()
    current = {
        "status": "Stopped",
        "site": "Like4Like",
        "chrome_profile": "old-profile",
        "proxy": None,
        "fallback_platform": None,
        "fallback_chain": None,
        "comment_templates": None,
    }
    updates = []
    monkeypatch.setattr(module, "get_agent", lambda _name: current)
    monkeypatch.setattr(module, "update_agent", lambda name, **fields: updates.append((name, fields)))
    monkeypatch.setattr(module, "append_agent_log", lambda *_args, **_kwargs: None)

    response = client.post(
        "/api/agents/update",
        json={"current_name": "worker", "name": "worker", "profile": "new-profile", "site": "KingdomLikes"},
    )

    assert response.status_code == 200
    assert ("worker", {"site": "KingdomLikes"}) in updates
    assert ("worker", {"chrome_profile": "new-profile"}) in updates


def test_agent_configuration_rejects_running_agent(monkeypatch):
    module, client = _dashboard_client()
    monkeypatch.setattr(module, "get_agent", lambda _name: {"status": "Running"})

    response = client.post(
        "/api/agents/update",
        json={"current_name": "worker", "name": "worker", "profile": "profile-a"},
    )

    assert response.status_code == 409


def test_agent_lifecycle_api_runs_valid_transition_sequence(monkeypatch):
    module, client = _dashboard_client()
    agent = {"status": "Stopped"}
    updates = []

    def update_agent(_name, **fields):
        agent.update(fields)
        updates.append(fields)

    monkeypatch.setattr(module, "get_agent", lambda _name: dict(agent))
    monkeypatch.setattr(module, "update_agent", update_agent)
    monkeypatch.setattr(module, "append_agent_log", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module.supervisor, "pause_agent", lambda _name: True)
    monkeypatch.setattr(module.supervisor, "stop_agent", lambda _name: (agent.update({"status": "Stopped"}) or True))

    def action(name):
        return client.post("/api/control", json={"name": "worker", "action": name})

    assert action("start").status_code == 200
    assert agent["status"] == "Awaiting Login"

    assert action("initialize").status_code == 409
    agent["status"] = "Login Success"
    assert action("initialize").status_code == 200
    assert agent["status"] == "Running"

    assert action("pause").status_code == 200
    assert agent["status"] == "Paused"
    assert action("resume").status_code == 200
    assert agent["status"] == "Running"

    assert action("stop").status_code == 200
    assert agent["status"] == "Stopped"
    assert action("restart").status_code == 200
    assert agent["status"] == "Awaiting Login"
    assert len(updates) >= 5


def test_agent_lifecycle_api_rejects_invalid_transitions(monkeypatch):
    module, client = _dashboard_client()
    agent = {"status": "Running"}
    monkeypatch.setattr(module, "get_agent", lambda _name: dict(agent))
    monkeypatch.setattr(module, "update_agent", lambda *_args, **_kwargs: None)

    assert client.post("/api/control", json={"name": "worker", "action": "start"}).status_code == 409
    assert client.post("/api/control", json={"name": "worker", "action": "pause"}).status_code == 200
    agent["status"] = "Stopped"
    assert client.post("/api/control", json={"name": "worker", "action": "resume"}).status_code == 409
    assert client.post("/api/control", json={"name": "worker", "action": "unknown"}).status_code == 400


def test_agent_lifecycle_api_reports_missing_agent(monkeypatch):
    module, client = _dashboard_client()
    monkeypatch.setattr(module, "get_agent", lambda _name: None)

    response = client.post("/api/control", json={"name": "missing", "action": "start"})
    assert response.status_code == 404


def test_agent_delete_waits_for_worker_shutdown(monkeypatch):
    module, client = _dashboard_client()
    removed = []
    monkeypatch.setattr(module, "get_agent", lambda _name: {"status": "Running"})
    monkeypatch.setattr(module.supervisor, "stop_agent", lambda _name: False)
    monkeypatch.setattr(module, "remove_agent", lambda name: removed.append(name))

    blocked = client.post("/api/agents/remove", json={"name": "worker"})
    assert blocked.status_code == 409
    assert removed == []

    monkeypatch.setattr(module.supervisor, "stop_agent", lambda _name: True)
    deleted = client.post("/api/agents/remove", json={"name": "worker"})
    assert deleted.status_code == 200
    assert removed == ["worker"]


def test_agent_delete_reports_missing_agent(monkeypatch):
    module, client = _dashboard_client()
    monkeypatch.setattr(module, "get_agent", lambda _name: None)

    response = client.post("/api/agents/remove", json={"name": "missing"})
    assert response.status_code == 404
