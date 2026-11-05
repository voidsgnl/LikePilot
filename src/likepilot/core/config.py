"""
LikePilot Configuration Management System
Provides dynamic configuration without restarts
"""
import json
import os
from likepilot.core.paths import runtime_path

CONFIG_FILE = runtime_path("config.json")

DEFAULT_CONFIG = {
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
    "performance": {
        "use_multiprocessing": False,  # Toggle between threading and multiprocessing
        "max_agents_per_process": 1,
        "process_restart_on_crash": True,
    },
    "dashboard": {
        "use_websockets": False,  # Toggle between polling and websockets
        "refresh_interval_seconds": 2,
        "chart_history_points": 200,
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


def get_proxy_list():
    """Get the configured proxy list."""
    config = load_config()
    return config.get("proxy", {}).get("proxy_list", [])


def add_proxy(proxy_string):
    """Add a proxy to the proxy list."""
    config = load_config()
    if "proxy" not in config:
        config["proxy"] = {"proxy_list": [], "enabled": False, "rotation_enabled": False}
    
    if "proxy_list" not in config["proxy"]:
        config["proxy"]["proxy_list"] = []
    
    if proxy_string not in config["proxy"]["proxy_list"]:
        config["proxy"]["proxy_list"].append(proxy_string)
        save_config(config)
        return True
    return False


def remove_proxy(proxy_string):
    """Remove a proxy from the proxy list."""
    config = load_config()
    if "proxy" in config and "proxy_list" in config["proxy"]:
        if proxy_string in config["proxy"]["proxy_list"]:
            config["proxy"]["proxy_list"].remove(proxy_string)
            save_config(config)
            return True
    return False


def is_captcha_enabled():
    """Check if CAPTCHA solving is enabled."""
    config = load_config()
    return config.get("captcha", {}).get("enabled", False)


def get_captcha_service():
    """Get the configured CAPTCHA service."""
    config = load_config()
    return config.get("captcha", {}).get("service", "2captcha")


def get_captcha_api_key():
    """Get the CAPTCHA service API key."""
    config = load_config()
    return config.get("captcha", {}).get("api_key", "")


def is_multiprocessing_enabled():
    """Check if multiprocessing mode is enabled."""
    config = load_config()
    return config.get("performance", {}).get("use_multiprocessing", False)


def is_websocket_enabled():
    """Check if WebSocket mode is enabled for dashboard."""
    config = load_config()
    return config.get("dashboard", {}).get("use_websockets", False)


def get_stealth_settings():
    """Get all stealth-related settings."""
    config = load_config()
    return config.get("stealth", {}).copy()


def get_automation_settings():
    """Get all automation-related settings."""
    config = load_config()
    return config.get("automation", {}).copy()
