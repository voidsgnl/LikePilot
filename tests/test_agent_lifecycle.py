import threading

from likepilot.core import runtime
from likepilot.integrations.providers.base import BaseBot


class _LifecycleBot(BaseBot):
    SITE_NAME = "LifecycleTest"
    LOGIN_URL = "https://example.invalid"

    def prepare(self):
        pass

    def update_credits(self):
        return True

    def detect_ready_state(self):
        return True

    def run(self):
        pass


class _Browser:
    def __init__(self):
        self.closed = False

    def quit(self):
        self.closed = True


def test_pause_stops_task_loop_but_preserves_browser_for_resume():
    bot = _LifecycleBot("user", "password")
    browser = _Browser()
    bot.driver = browser
    bot.is_running = True

    assert bot.pause() is True
    assert bot.is_running is False
    assert bot.exit_reason == "paused"
    assert bot.driver is browser
    assert browser.closed is False


def test_pause_is_idempotent_when_bot_is_not_running():
    bot = _LifecycleBot("user", "password")

    assert bot.pause() is False
    assert bot.exit_reason is None


def test_start_worker_does_not_launch_for_stopped_agent(monkeypatch):
    supervisor = runtime.AgentSupervisor()
    monkeypatch.setattr(runtime, "get_agent", lambda _name: {"status": "Stopped"})
    supervisor._worker = lambda _name: None

    supervisor._start_worker("agent-a")

    assert supervisor.active_agents == {}


def test_stop_agent_joins_worker_before_releasing_runtime(monkeypatch):
    supervisor = runtime.AgentSupervisor()
    stopped = threading.Event()
    updates = []
    monkeypatch.setattr(runtime, "get_agent", lambda _name: {"status": "Running"})
    monkeypatch.setattr(runtime, "update_agent", lambda _name, **fields: updates.append(fields))
    monkeypatch.setattr(runtime, "append_agent_log", lambda *_args, **_kwargs: None)

    class _Bot:
        def stop(self):
            stopped.set()

    worker = threading.Thread(target=lambda: stopped.wait(timeout=1))
    worker.start()
    supervisor.active_agents["agent-a"] = runtime.AgentRuntime(worker)
    supervisor.active_agents["agent-a"].bot = _Bot()
    supervisor.cooldowns["agent-a"] = 123

    assert supervisor.stop_agent("agent-a", timeout_seconds=0.5) is True
    assert not worker.is_alive()
    assert "agent-a" not in supervisor.active_agents
    assert "agent-a" not in supervisor.cooldowns
    assert updates == [{"status": "Stopped", "session_started_at": None}]



def test_provider_platform_rotation_never_leaves_provider_capabilities():
    supervisor = runtime.AgentSupervisor()

    assert supervisor._next_platform(
        "YouTube Subs",
        ["YouTube Subs", "YouTube Likes"],
    ) == "YouTube Likes"
    assert supervisor._next_platform(
        "YouTube Likes",
        ["YouTube Subs", "YouTube Likes"],
    ) == "YouTube Subs"


def test_fallback_chain_ignores_platforms_not_supported_by_provider():
    supervisor = runtime.AgentSupervisor()

    assert supervisor._next_from_chain(
        "YouTube Subs",
        "Twitter, YouTube Subs, Instagram, YouTube Likes",
        ["YouTube Subs", "YouTube Likes"],
    ) == "YouTube Likes"
