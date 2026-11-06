"""
LikePilot Configuration Management System
Provides dynamic configuration without restarts
"""
import json
import os
from likepilot.core.paths import runtime_path

CONFIG_FILE = runtime_path("config.json")

DEFAULT_CONFIG = {
    "browser": {
        "default": "chrome",
    },
    "stealth": {
        "randomize_fingerprint": True,
        "randomize_user_agent": True,
        "randomize_viewport": True,
        "human_behavior": True,
        "bezier_mouse": True,
        "random_scroll": True,
        "min_delay_between_actions": 2,
        "max_delay_between_actions": 8,
    },
    "proxy": {
        "enabled": False,
        "rotation_enabled": False,
        "rotation_threshold": 5,  # Rotate after N failures
        "proxy_list": [],
    },
    "captcha": {
        "enabled": False,
        "service": "2captcha",  # Options: 2captcha, capsolver
        "api_key": "",
        "max_retries": 3,
    },
    "dashboard": {
        "refresh_interval_seconds": 2,
        "chart_history_points": 200,
    },
    "notifications": {
        "enabled": False,
        "discord_webhook": "",
        "telegram_bot_token": "",
        "telegram_chat_id": "",
        "email_enabled": False,
        "email_smtp": "",
        "email_from": "",
        "email_to": "",
        "high_credits_earned": True,
        "rate_limiting_detected": True,
        "agent_crashed": True,
        "daily_summary": True,
        "system_errors": True,
        "milestones": True,
    },
    "security": {
        "encrypt_credentials": False,
        "auto_lock_on_idle": False,
        "idle_timeout_minutes": 30,
    },
    "automation": {
        "auto_switch_platform": True,
        "max_consecutive_failures": 10,
        "cooldown_on_failure_seconds": 60,
        "credit_verification_timeout": 12,
    }
}


def load_config():
    """Load configuration from file, creating defaults if needed."""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        # Merge with defaults to ensure all keys exist
        return _merge_configs(DEFAULT_CONFIG, config)
    except (json.JSONDecodeError, IOError):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()


def save_config(config):
    """Save configuration to file."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    return True


def _merge_configs(default, override):
    """Recursively merge override config into default config."""
    result = default.copy()
    for key, value in override.items():
        if key in result:
            if isinstance(value, dict) and isinstance(result[key], dict):
                result[key] = _merge_configs(result[key], value)
            else:
                result[key] = value
    return result


def get_config_value(path, default=None):
    """
    Get a config value using dot notation.
    Example: get_config_value("stealth.randomize_fingerprint")
    """
    config = load_config()
    keys = path.split(".")
    value = config
    
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    
    return value


def set_config_value(path, value):
    """
    Set a config value using dot notation.
    Example: set_config_value("stealth.randomize_fingerprint", True)
    """
    config = load_config()
    keys = path.split(".")
    
    current = config
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value
    save_config(config)
    return True


def update_config_section(section, updates):
    """Update an entire configuration section."""
    config = load_config()
    if section in config:
        config[section].update(updates)
    else:
        config[section] = updates
    save_config(config)
    return True


def reset_to_defaults():
    """Reset configuration to default values."""
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()


def _read_encrypted_config_secret(name, path):
    """Read a config-backed secret, migrating its legacy JSON value once."""
    from likepilot.core.state import get_secret, set_secret

    stored = get_secret(name)
    if stored:
        return stored

    legacy = get_config_value(path, "")
    if legacy:
        set_secret(name, legacy)
        set_config_value(path, "")
        return legacy
    return ""


def get_proxy_list():
    """Return proxy entries from encrypted storage, migrating legacy JSON entries."""
    import json
    from likepilot.core.state import get_secret, set_secret

    stored = get_secret("config.proxy.proxy_list")
    if stored:
        try:
            proxies = json.loads(stored)
            from likepilot.core.security import register_secret
            for proxy in proxies:
                register_secret(proxy)
            return proxies
        except (TypeError, json.JSONDecodeError):
            raise ValueError("Stored proxy configuration is invalid; refusing to discard it.")

    legacy = get_config_value("proxy.proxy_list", []) or []
    if legacy:
        from likepilot.core.security import register_secret
        for proxy in legacy:
            register_secret(proxy)
        set_secret("config.proxy.proxy_list", json.dumps(legacy))
        set_config_value("proxy.proxy_list", [])
    return legacy


def _save_proxy_list(proxies):
    import json
    from likepilot.core.state import set_secret

    set_secret("config.proxy.proxy_list", json.dumps(proxies))


def add_proxy(proxy_string):
    """Add a proxy entry to encrypted proxy storage."""
    proxies = get_proxy_list()
    if proxy_string in proxies:
        return False
    proxies.append(proxy_string)
    _save_proxy_list(proxies)
    return True


def remove_proxy(proxy_string):
    """Remove a proxy entry from encrypted proxy storage."""
    proxies = get_proxy_list()
    if proxy_string not in proxies:
        return False
    proxies.remove(proxy_string)
    _save_proxy_list(proxies)
    return True


def get_notification_secret(name):
    """Read and migrate a notification token from legacy JSON configuration."""
    allowed = {
        "discord_webhook": "notifications.discord_webhook",
        "telegram_bot_token": "notifications.telegram_bot_token",
    }
    if name not in allowed:
        raise ValueError(f"Unsupported notification secret: {name}")
    return _read_encrypted_config_secret(f"config.notifications.{name}", allowed[name])


def is_captcha_enabled():
    """Check if CAPTCHA solving is enabled."""
    config = load_config()
    return config.get("captcha", {}).get("enabled", False)


def get_captcha_service():
    """Get the configured CAPTCHA service."""
    config = load_config()
    return config.get("captcha", {}).get("service", "2captcha")


def get_captcha_api_key():
    """Read the CAPTCHA key from encrypted storage, migrating legacy config values."""
    from likepilot.core.state import get_secret, set_secret

    stored = get_secret("captcha.api_key")
    if stored:
        return stored

    legacy = get_config_value("captcha.api_key", "")
    if legacy:
        set_secret("captcha.api_key", legacy)
        set_config_value("captcha.api_key", "")
        return legacy
    return ""


def get_stealth_settings():
    """Get all stealth-related settings."""
    config = load_config()
    return config.get("stealth", {}).copy()


def get_automation_settings():
    """Get all automation-related settings."""
    config = load_config()
    return config.get("automation", {}).copy()
