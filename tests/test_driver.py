import pytest

from likepilot.core import driver
from likepilot.core.driver import inject_stealth


class FakeFirefoxDriver:
    capabilities = {"browserName": "firefox"}

    def execute_cdp_cmd(self, *_args, **_kwargs):
        raise AssertionError("Firefox must not receive Chrome CDP commands")


class FakeChromeDriver:
    capabilities = {"browserName": "chrome"}

    def __init__(self):
        self.commands = []

    def execute_cdp_cmd(self, command, params):
        self.commands.append((command, params))


def test_firefox_skips_chrome_cdp_stealth():
    inject_stealth(FakeFirefoxDriver())


def test_chrome_keeps_existing_cdp_stealth():
    driver_instance = FakeChromeDriver()

    inject_stealth(driver_instance)

    assert len(driver_instance.commands) == 1
    assert driver_instance.commands[0][0] == "Page.addScriptToEvaluateOnNewDocument"


@pytest.mark.parametrize(
    ("browser", "profile_name", "directory"),
    [
        ("chrome", "Default", "user_Default"),
        ("firefox", "Profile 4", "firefox_user_Profile 4"),
    ],
)
def test_profile_directory_uses_data_directory(tmp_path, monkeypatch, browser, profile_name, directory):
    monkeypatch.setattr(driver, "get_runtime_root", lambda: str(tmp_path))

    profile_path = driver._profile_directory(browser, profile_name)

    assert profile_path == str(tmp_path / "data" / "profiles" / directory)
    assert (tmp_path / "data" / "profiles" / directory).is_dir()
    assert not (tmp_path / "profiles" / directory).exists()


def test_profile_directory_migrates_legacy_profile_without_losing_contents(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, "get_runtime_root", lambda: str(tmp_path))
    legacy = tmp_path / "profiles" / "user_Default"
    legacy.mkdir(parents=True)
    (legacy / "Cookies").write_bytes(b"existing-session-data")

    profile_path = driver._profile_directory("chrome", "Default")

    migrated = tmp_path / "data" / "profiles" / "user_Default"
    assert profile_path == str(migrated)
    assert (migrated / "Cookies").read_bytes() == b"existing-session-data"
    assert not legacy.exists()


def test_profile_directory_refuses_to_overwrite_duplicate_legacy_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, "get_runtime_root", lambda: str(tmp_path))
    legacy = tmp_path / "profiles" / "user_Default"
    current = tmp_path / "data" / "profiles" / "user_Default"
    legacy.mkdir(parents=True)
    current.mkdir(parents=True)
    (legacy / "legacy-marker").write_text("legacy")
    (current / "current-marker").write_text("current")

    with pytest.raises(FileExistsError, match="Both legacy and new"):
        driver._profile_directory("chrome", "Default")

    assert (legacy / "legacy-marker").read_text() == "legacy"
    assert (current / "current-marker").read_text() == "current"


def test_chrome_options_apply_proxy_and_persistent_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, "_profile_directory", lambda browser, profile: str(tmp_path / "chrome-profile"))

    options = driver.get_chrome_options(
        profile_name="Agent A",
        proxy="http://proxy.example:8080",
        startup_url="https://example.com",
    )

    assert "--proxy-server=http://proxy.example:8080" in options.arguments
    assert f"--user-data-dir={tmp_path / 'chrome-profile'}" in options.arguments
    assert "https://example.com" in options.arguments


def test_firefox_options_apply_http_proxy_and_persistent_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, "_profile_directory", lambda browser, profile: str(tmp_path / "firefox-profile"))
    monkeypatch.delenv("LIKEPILOT_FIREFOX_BINARY", raising=False)

    options = driver.get_firefox_options(
        profile_name="Agent A",
        proxy="http://proxy.example:8080",
    )
    capabilities = options.to_capabilities()
    firefox_options = capabilities["moz:firefoxOptions"]

    assert "-profile" in firefox_options["args"]
    assert str(tmp_path / "firefox-profile") in firefox_options["args"]
    assert firefox_options["prefs"]["network.proxy.type"] == 1
    assert firefox_options["prefs"]["network.proxy.http"] == "proxy.example"
    assert firefox_options["prefs"]["network.proxy.http_port"] == 8080
    assert firefox_options["prefs"]["network.proxy.ssl"] == "proxy.example"
    assert firefox_options["prefs"]["network.proxy.ssl_port"] == 8080


def test_firefox_options_apply_socks5_proxy(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, "_profile_directory", lambda browser, profile: str(tmp_path / "firefox-profile"))
    monkeypatch.delenv("LIKEPILOT_FIREFOX_BINARY", raising=False)

    options = driver.get_firefox_options(proxy="socks5://proxy.example:1080")
    prefs = options.to_capabilities()["moz:firefoxOptions"]["prefs"]

    assert prefs["network.proxy.type"] == 1
    assert prefs["network.proxy.socks"] == "proxy.example"
    assert prefs["network.proxy.socks_port"] == 1080
    assert prefs["network.proxy.socks_version"] == 5


@pytest.mark.parametrize("proxy", [
    "http://user:password@proxy.example:8080",
    "socks5://user:password@proxy.example:1080",
])
def test_firefox_rejects_authenticated_proxy_with_clear_error(tmp_path, monkeypatch, proxy):
    monkeypatch.setattr(driver, "_profile_directory", lambda browser, profile: str(tmp_path / "firefox-profile"))
    monkeypatch.delenv("LIKEPILOT_FIREFOX_BINARY", raising=False)

    with pytest.raises(ValueError, match="unauthenticated proxies only"):
        driver.get_firefox_options(proxy=proxy)


def test_firefox_driver_factory_uses_selected_browser_and_opens_startup_url(monkeypatch):
    calls = {}
    fake_driver = type("FakeDriver", (), {"get": lambda self, url: calls.setdefault("url", url)})()
    fake_options = object()

    monkeypatch.setattr(driver, "get_config_value", lambda *_args: "firefox")
    monkeypatch.setattr(driver, "get_firefox_options", lambda *args, **kwargs: fake_options)
    def create_firefox(options):\n        calls["options"] = options\n        return fake_driver\n\n    monkeypatch.setattr(driver.webdriver, "Firefox", create_firefox)

    created = driver.create_stealth_driver(profile_name="Agent A", startup_url="https://example.com")

    assert calls["options"] is fake_options
    assert calls["url"] == "https://example.com"
    assert created is not None
