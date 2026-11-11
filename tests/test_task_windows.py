from likepilot.integrations.providers.base import BaseBot


class _Switch:
    def __init__(self, driver):
        self.driver = driver

    def window(self, handle):
        if handle not in self.driver.window_handles:
            raise RuntimeError("unknown window")
        self.driver.current_window_handle = handle


class _Driver:
    def __init__(self, handles):
        self.window_handles = list(handles)
        self.current_window_handle = handles[0]
        self.switch_to = _Switch(self)

    def close(self):
        self.window_handles.remove(self.current_window_handle)
        if self.window_handles:
            self.current_window_handle = self.window_handles[0]


class _WindowBot(BaseBot):
    SITE_NAME = "Test"
    LOGIN_URL = "https://example.invalid"

    def prepare(self):
        pass

    def update_credits(self):
        return True

    def detect_ready_state(self):
        return True

    def run(self):
        pass


def test_wait_for_popup_returns_only_a_new_window():
    bot = _WindowBot("user", "password")
    bot.driver = _Driver(["provider", "older-popup"])
    bot._known_window_handles = {"provider", "older-popup"}
    bot.driver.window_handles.append("new-task-popup")

    assert bot.wait_for_popup("provider", timeout_seconds=0.1) == "new-task-popup"


def test_task_window_cannot_close_before_credit_collection():
    bot = _WindowBot("user", "password")
    bot.driver = _Driver(["provider", "task"])
    bot._known_window_handles = {"provider", "task"}

    assert bot.close_task_window("task", "provider") is False
    assert "task" in bot.driver.window_handles


def test_task_window_closes_after_credit_collection_and_restores_provider():
    bot = _WindowBot("user", "password")
    bot.driver = _Driver(["provider", "task"])
    bot._known_window_handles = {"provider", "task"}

    assert bot.close_task_window("task", "provider", credits_collected=True) is True
    assert bot.driver.window_handles == ["provider"]
    assert bot.driver.current_window_handle == "provider"


class _DelayedCreditBot(_WindowBot):
    def __init__(self):
        super().__init__("user", "password")
        self.credit_checks = 0

    def update_credits(self):
        self.credit_checks += 1
        return self.credit_checks >= 2


def test_credit_collection_waits_for_delayed_provider_update():
    bot = _DelayedCreditBot()

    assert bot.wait_for_credit_increase(timeout_seconds=0.5, poll_interval=0.01) is True
    assert bot.credit_checks == 2


def test_credit_collection_times_out_without_confirmed_increase():
    bot = _WindowBot("user", "password")
    bot.update_credits = lambda: False

    assert bot.wait_for_credit_increase(timeout_seconds=0.02, poll_interval=0.01) is False
