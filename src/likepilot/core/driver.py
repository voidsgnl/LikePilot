""""Browser driver factory for the globally selected LikePilot browser."""

import os
from urllib.parse import urlsplit

import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions

from likepilot.core.config import get_config_value
from likepilot.core.paths import get_runtime_root


def _env_flag(name, default=True):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _env_int(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value.strip())
    except (TypeError, ValueError):
        return default


def _safe_profile_name(profile_name):
    profile_name = profile_name or os.getenv("CHROME_PROFILE", "Default")
    return "".join(char for char in profile_name if char.isalnum() or char in (" ", "-", "_")).strip() or "Default"


def _profile_directory(browser, profile_name=None):
    safe_name = _safe_profile_name(profile_name)
    prefix = "user_" if browser == "chrome" else "firefox_user_"
    profile_dirname = f"{prefix}{safe_name}"

    runtime_root = get_runtime_root()
    legacy_path = os.path.join(runtime_root, "profiles", profile_dirname)
    data_profiles = os.path.join(runtime_root, "data", "profiles")
    path = os.path.join(data_profiles, profile_dirname)

    os.makedirs(data_profiles, exist_ok=True)
    legacy_exists = os.path.isdir(legacy_path)
    destination_exists = os.path.exists(path)

    if legacy_exists and destination_exists:
        raise FileExistsError(
            "Both legacy and new LikePilot browser profiles exist for "
            f"{browser} profile {safe_name!r}. Neither was changed. "
            f"Compare and back up '{legacy_path}' and '{path}' before "
            "resolving the duplicate."
        )
    if legacy_exists:
        # Rename on the same filesystem to preserve the complete browser
        # profile (including cookies and session databases) without copying.
        os.replace(legacy_path, path)
    else:
        os.makedirs(path, exist_ok=True)

    print(f"Using dedicated {browser.title()} profile: {path}")
    return path


def get_chrome_options(profile_name=None, proxy=None, startup_url=None):
    """Build Chrome options while preserving existing Chrome profile behavior."""
    options = uc.ChromeOptions()
    for argument in (
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--disable-features=IsolateOrigins,site-per-process",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-session-crashed-bubble",
        "--disable-features=Translate,NotificationTriggers,OptimizationHints",
        "--disable-background-networking",
        "--disable-sync",
        "--homepage=about:blank",
    ):
        options.add_argument(argument)

    compact_mode = _env_flag("CHROME_COMPACT_MODE", True)
    width = max(360, _env_int("CHROME_WINDOW_WIDTH", 540))
    height = max(640, _env_int("CHROME_WINDOW_HEIGHT", 900))
    x = max(0, _env_int("CHROME_WINDOW_X", 24))
    y = max(0, _env_int("CHROME_WINDOW_Y", 24))
    if compact_mode:
        options.add_argument(f"--window-size={width},{height}")
        options.add_argument(f"--window-position={x},{y}")

    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 2,
        "session.restore_on_startup": 4,
        "session.startup_urls": [],
        "homepage": "about:blank",
        "homepage_is_newtabpage": False,
    })
    if startup_url:
        options.add_argument(startup_url)
    options.add_argument(f"--user-data-dir={_profile_directory('chrome', profile_name)}")
    if proxy:
        options.add_argument(f"--proxy-server={proxy}")
    return options


def get_firefox_options(profile_name=None, proxy=None, startup_url=None, headless=False):
    """Build Firefox options and a dedicated persistent Firefox profile."""
    options = FirefoxOptions()

    # Ubuntu's Firefox Snap launcher is not a Firefox binary from
    # geckodriver's perspective. Point Selenium at the executable inside
    # the mounted Snap; allow an explicit override for other installations.
    firefox_binary = os.getenv("LIKEPILOT_FIREFOX_BINARY")
    if not firefox_binary and os.path.isfile(
        "/snap/firefox/current/usr/lib/firefox/firefox"
    ):
        firefox_binary = "/snap/firefox/current/usr/lib/firefox/firefox"
    if firefox_binary:
        if not os.path.isfile(firefox_binary) or not os.access(firefox_binary, os.X_OK):
            raise FileNotFoundError(
                f"Firefox binary is not executable: {firefox_binary}"
            )
        options.binary_location = firefox_binary
    if headless:
        options.add_argument("-headless")
    options.set_preference("dom.notifications.enabled", False)
    options.set_preference("browser.startup.page", 0)
    options.set_preference("browser.shell.checkDefaultBrowser", False)
    options.set_preference("toolkit.telemetry.enabled", False)

    profile_path = _profile_directory("firefox", profile_name)
    options.add_argument("-profile")
    options.add_argument(profile_path)

    if proxy:
        parsed = urlsplit(proxy if "://" in proxy else f"http://{proxy}")
        if not parsed.hostname or not parsed.port:
            raise ValueError("Firefox proxy must include a hostname and port.")
        scheme = parsed.scheme.lower()
        options.set_preference("network.proxy.type", 1)
        if scheme.startswith("socks"):
            options.set_preference("network.proxy.socks", parsed.hostname)
            options.set_preference("network.proxy.socks_port", parsed.port)
            options.set_preference("network.proxy.socks_version", 5 if scheme == "socks5" else 4)
        else:
            for protocol in ("http", "ssl", "ftp"):
                options.set_preference(f"network.proxy.{protocol}", parsed.hostname)
                options.set_preference(f"network.proxy.{protocol}_port", parsed.port)
        options.set_preference("network.proxy.no_proxies_on", "localhost, 127.0.0.1")
        if parsed.username or parsed.password:
            raise ValueError("Firefox currently supports unauthenticated proxies only; remove proxy credentials or use a compatible proxy endpoint.")
    return options


def create_stealth_driver(headless=False, proxy=None, profile_name=None, startup_url=None, browser=None):
    """Create a driver using the global dashboard browser setting by default."""
    selected = (browser or get_config_value("browser.default", "chrome") or "chrome").strip().lower()
    if selected not in {"chrome", "firefox"}:
        raise ValueError(f"Unsupported browser selection: {selected}")

    if selected == "firefox":
        print(f"[DEBUG] Launching Firefox for profile: {profile_name}")
        options = get_firefox_options(profile_name, proxy, startup_url, headless=headless)
        driver = webdriver.Firefox(options=options)
        if startup_url:
            driver.get(startup_url)
        return driver

    print(f"[DEBUG] Launching Chrome for profile: {profile_name}")
    version_main = _env_int("LIKEPILOT_CHROME_VERSION", 0)
    driver_options = {
        "options": get_chrome_options(profile_name, proxy, startup_url),
        "headless": headless,
        "use_subprocess": True,
    }
    if version_main > 0:
        driver_options["version_main"] = version_main

    try:
        return uc.Chrome(**driver_options)
    except Exception as error:
        print(f"Chrome subprocess launch failed: {error}. Trying fallback mode...")
        fallback_options = {
            "options": get_chrome_options(profile_name, proxy, startup_url),
            "headless": headless,
            "use_subprocess": False,
        }
        if version_main > 0:
            fallback_options["version_main"] = version_main
        return uc.Chrome(**fallback_options)


def inject_stealth(driver):
    """Apply the existing Chrome-only CDP tweak; Firefox uses WebDriver."""
    browser_name = (getattr(driver, "capabilities", {}) or {}).get("browserName", "")
    if str(browser_name).strip().lower() != "chrome":
        return

    execute_cdp = getattr(driver, "execute_cdp_cmd", None)
    if not callable(execute_cdp):
        return
    execute_cdp("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
    })
