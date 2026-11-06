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
