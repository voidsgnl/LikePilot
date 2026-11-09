from likepilot.integrations.providers import base
from likepilot.integrations.providers.base import BaseBot


class _ClickBot(BaseBot):
    SITE_NAME = "ClickTest"
    LOGIN_URL = "https://example.invalid"

    def prepare(self):
        pass

    def update_credits(self):
        return False

    def detect_ready_state(self):
        return False

    def run(self):
        pass


class _Driver:
    def __init__(self, *, fail_scroll=False):
        self.scripts = []
        self.fail_scroll = fail_scroll

    def execute_script(self, script, element):
        self.scripts.append(script)
        if "scrollIntoView" in script and self.fail_scroll:
            raise RuntimeError("scroll failed")


class _Element:
    def __init__(self, *, fail_click=False):
        self.clicked = False
        self.fail_click = fail_click

    def click(self):
        if self.fail_click:
            raise RuntimeError("native click failed")
        self.clicked = True


class _ActionChain:
    def __init__(self, driver):
        self.driver = driver

    def move_to_element(self, _element):
        return self

    def pause(self, _seconds):
        return self

    def click(self):
        return self

    def perform(self):
        self.driver.action_chain_clicked = True


def test_safe_click_is_available_on_shared_base_bot(monkeypatch):
    monkeypatch.setattr(base, "ActionChains", _ActionChain)
    bot = _ClickBot("user", "password")
    bot.driver = _Driver()
    element = _Element()

    assert bot.safe_click(element) is True
    assert bot.driver.action_chain_clicked is True


def test_safe_click_falls_back_to_native_element_click(monkeypatch):
    monkeypatch.setattr(base, "ActionChains", _ActionChain)
    bot = _ClickBot("user", "password")
    bot.driver = _Driver(fail_scroll=True)
    element = _Element()

    assert bot.safe_click(element) is True
    assert element.clicked is True


def test_safe_click_falls_back_to_javascript_click(monkeypatch):
    monkeypatch.setattr(base, "ActionChains", _ActionChain)
    bot = _ClickBot("user", "password")
    bot.driver = _Driver(fail_scroll=True)
    element = _Element(fail_click=True)

    assert bot.safe_click(element) is True
    assert any("arguments[0].click()" in script for script in bot.driver.scripts)


def test_safe_click_returns_false_without_driver():
    bot = _ClickBot("user", "password")

    assert bot.safe_click(_Element()) is False
