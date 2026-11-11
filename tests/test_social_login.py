from likepilot.integrations.providers import base


class _LoginBot(base.BaseBot):
    SITE_NAME = "SocialLoginTest"
    LOGIN_URL = "https://provider.example/login"

    def prepare(self):
        pass

    def update_credits(self):
        return False

    def detect_ready_state(self):
        return True

    def run(self):
        pass


class _Element:
    def is_displayed(self):
        return True


class _Driver:
    def __init__(self, url, *, password_visible=False, body_text="", cookies=None):
        self.current_url = url
        self.password_visible = password_visible
        self.body_text = body_text
        self.cookies = cookies or []
        self.password_lookups = 0

    def find_elements(self, by, selector):
        if selector == "input[type='password']":
            self.password_lookups += 1
            return [_Element()] if self.password_visible else []
        return []

    def execute_script(self, script):
        return self.body_text

    def get_cookies(self):
        return self.cookies


def _bot(driver):
    bot = _LoginBot("user", "password")
    bot.driver = driver
    bot.is_running = True
    bot.agent_name = "social-login-agent"
    bot.status_updates = []
    bot.logs = []
    bot.heartbeat = lambda status=None: bot.status_updates.append(status)
    bot.emit_log = lambda message, level="INFO": bot.logs.append((level, message))
    return bot


def test_authenticated_social_session_continues_without_waiting():
    driver = _Driver(
        "https://www.instagram.com/p/example/",
        cookies=[{"name": "sessionid", "value": "present"}],
    )
    bot = _bot(driver)

    assert bot.wait_for_social_login("Instagram", timeout_seconds=0.1) is True
    assert bot.status_updates == []


def test_instagram_login_gate_waits_then_resumes_same_task(monkeypatch):
    driver = _Driver(
        "https://www.instagram.com/accounts/login/",
        password_visible=True,
    )
    bot = _bot(driver)

    def finish_manual_login(_seconds):
        driver.current_url = "https://www.instagram.com/p/example/"
        driver.password_visible = False
        driver.cookies = [{"name": "sessionid", "value": "authenticated"}]

    monkeypatch.setattr(base.time, "sleep", finish_manual_login)

    assert bot.wait_for_social_login("Instagram", timeout_seconds=1, poll_interval=0.01) is True
    assert bot.status_updates == ["Awaiting Social Login", "Running"]
    assert any("task will resume automatically" in message for _, message in bot.logs)


def test_google_two_factor_challenge_waits_for_youtube_session(monkeypatch):
    driver = _Driver("https://accounts.google.com/v3/signin/challenge/pwd")
    bot = _bot(driver)

    def finish_verification(_seconds):
        driver.current_url = "https://www.youtube.com/watch?v=example"
        driver.cookies = [{"name": "SID", "value": "authenticated"}]

    monkeypatch.setattr(base.time, "sleep", finish_verification)

    assert bot.wait_for_social_login("YouTube", timeout_seconds=1, poll_interval=0.01) is True
    assert bot.status_updates == ["Awaiting Social Login", "Running"]


def test_login_wait_exits_when_agent_is_stopped(monkeypatch):
    driver = _Driver(
        "https://www.tiktok.com/login",
        password_visible=True,
    )
    bot = _bot(driver)

    monkeypatch.setattr(base.time, "sleep", lambda _seconds: setattr(bot, "is_running", False))

    assert bot.wait_for_social_login("TikTok", timeout_seconds=1, poll_interval=0.01) is False
    assert bot.status_updates == ["Awaiting Social Login"]


def test_plain_log_in_navigation_text_is_not_a_login_gate():
    driver = _Driver(
        "https://x.com/home",
        body_text="Home\nExplore\nLog in",
        cookies=[{"name": "auth_token", "value": "present"}],
    )
    bot = _bot(driver)

    assert bot._social_login_gate_present("X", ("x.com", "twitter.com")) is False


def test_login_gate_is_not_cleared_until_auth_cookie_exists(monkeypatch):
    driver = _Driver(
        "https://www.facebook.com/login/",
        password_visible=True,
    )
    bot = _bot(driver)
    sleep_count = {"value": 0}

    def partial_login(_seconds):
        sleep_count["value"] += 1
        driver.current_url = "https://www.facebook.com/"
        driver.password_visible = False
        if sleep_count["value"] >= 2:
            driver.cookies = [
                {"name": "c_user", "value": "authenticated"},
                {"name": "xs", "value": "session"},
            ]

    monkeypatch.setattr(base.time, "sleep", partial_login)

    assert bot.wait_for_social_login("Facebook", timeout_seconds=1, poll_interval=0.01) is True
    assert sleep_count["value"] >= 2
    assert bot.status_updates == ["Awaiting Social Login", "Running"]


def test_platform_cookie_requirements_are_defined_for_all_supported_networks():
    expected = {
        "Instagram Likes": {"sessionid"},
        "YouTube Subs": {"sid", "hsid", "ssid", "sapisid", "__secure-1psid", "login_info"},
        "Twitter Retweets": {"auth_token"},
        "Facebook Likes": {"c_user", "xs"},
        "TikTok Likes": {"sessionid", "sid_tt", "sid_guard"},
    }
    for platform, cookies in expected.items():
        _label, domains, required_cookies = _LoginBot._social_platform_details(platform)
        assert domains
        assert cookies.issubset(required_cookies)


def test_all_task_adapter_families_use_social_login_recovery():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "src" / "likepilot" / "integrations"
    adapters = (
        root / "networks" / "instagram.py",
        root / "networks" / "youtube.py",
        root / "networks" / "x.py",
        root / "networks" / "facebook.py",
        root / "networks" / "tiktok.py",
        root / "providers" / "kingdomlikes.py",
        root / "providers" / "youlikehits.py",
    )
    for adapter in adapters:
        assert "wait_for_social_login()" in adapter.read_text(encoding="utf-8"), adapter.name


def test_public_task_page_without_session_still_waits_for_sign_in(monkeypatch):
    driver = _Driver("https://www.instagram.com/p/public-example/")
    bot = _bot(driver)

    def finish_login(_seconds):
        driver.cookies = [{"name": "sessionid", "value": "authenticated"}]

    monkeypatch.setattr(base.time, "sleep", finish_login)

    assert bot.wait_for_social_login("Instagram", timeout_seconds=1, poll_interval=0.01) is True
    assert bot.status_updates == ["Awaiting Social Login", "Running"]
