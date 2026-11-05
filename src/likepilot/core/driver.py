import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
import os
import random
import time
import shutil
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


def get_options(profile_name=None, proxy=None, startup_url=None):
    """Creates a dedicated bot profile that persists logins."""
    options = uc.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu") 
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-session-crashed-bubble")
    options.add_argument("--disable-features=Translate,NotificationTriggers,OptimizationHints")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-sync")
    options.add_argument("--homepage=about:blank")
    compact_mode = _env_flag("CHROME_COMPACT_MODE", True)
    window_width = max(360, _env_int("CHROME_WINDOW_WIDTH", 540))
    window_height = max(640, _env_int("CHROME_WINDOW_HEIGHT", 900))
    window_x = max(0, _env_int("CHROME_WINDOW_X", 24))
    window_y = max(0, _env_int("CHROME_WINDOW_Y", 24))
    if compact_mode:
        options.add_argument(f"--window-size={window_width},{window_height}")
        options.add_argument(f"--window-position={window_x},{window_y}")
    options.add_experimental_option(
        "prefs",
        {
            "profile.default_content_setting_values.notifications": 2,
            "session.restore_on_startup": 4,
            "session.startup_urls": [],
            "homepage": "about:blank",
            "homepage_is_newtabpage": False,
        },
    )
    if startup_url:
        options.add_argument(startup_url)
    
    # Use the provided profile name or fallback to Default
    if not profile_name:
        profile_name = os.getenv("CHROME_PROFILE", "Default")
    
    # Create a dedicated folder in the project for the bot's session
    project_dir = get_runtime_root()
    # Sanitize profile name for directory usage
    safe_profile_name = "".join([c for c in profile_name if c.isalnum() or c in (' ', '-', '_')]).strip()
    bot_profile_dir = os.path.join(project_dir, "profiles", f"user_{safe_profile_name}")
    os.makedirs(bot_profile_dir, exist_ok=True)
    
    print(f"Using dedicated bot profile: {bot_profile_dir}")
    if compact_mode:
        print(f"Using compact browser window: {window_width}x{window_height} at {window_x},{window_y}")
    options.add_argument(f"--user-data-dir={bot_profile_dir}")
    if proxy:
        options.add_argument(f"--proxy-server={proxy}")
    
    # Remove any old lock files if they exist
    lock = os.path.join(bot_profile_dir, "SingletonLock")
    if os.path.exists(lock):
        try: os.remove(lock)
        except: pass

    return options

def create_stealth_driver(headless=False, proxy=None, profile_name=None, startup_url=None):
    """
    Creates a highly undetectable Chrome driver instance.
    Prioritizes subprocess mode to avoid long timeouts on Windows.
    """
    # Attempt 1: Subprocess mode (Faster and more stable for custom profiles on Windows)
    try:
        print(f"[DEBUG] Launching Chrome (Subprocess Mode) for profile: {profile_name}")
        driver = uc.Chrome(
            options=get_options(profile_name=profile_name, proxy=proxy, startup_url=startup_url),
            headless=headless,
            use_subprocess=True,
            version_main=145
        )
        return driver
    except Exception as e:
        print(f"Subprocess launch failed: {e}. Trying fallback mode...")
        try:
            # Fallback
            driver = uc.Chrome(
                options=get_options(profile_name=profile_name, proxy=proxy, startup_url=startup_url),
                headless=headless,
                use_subprocess=False,
                version_main=145
            )
            return driver
        except Exception as e2:
            print(f"Critical driver failure: {e2}")
            raise e2

def inject_stealth(driver):
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """
    })
