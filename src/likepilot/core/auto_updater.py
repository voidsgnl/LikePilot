"""
LikePilot Auto-Updater
Checks for updates and applies them automatically
"""
import requests
import time
from likepilot.core.config import get_config_value

class AutoUpdater:
    def __init__(self):
        self.enabled = get_config_value("updater.enabled", False)
        self.check_interval_hours = get_config_value("updater.check_interval_hours", 24)
        self.auto_install = get_config_value("updater.auto_install", False)
        self.github_repo = get_config_value("updater.github_repo", "yourusername/likepilot")
        self.current_version = get_config_value("version", "1.0.0")

        self.last_check = 0
        self.update_available = False
        self.latest_version = None
        self.release_info = None

    def check_for_updates(self):
        """Check if updates are available"""
        if not self.enabled:
            return False

        current_time = time.time()
        if current_time - self.last_check < (self.check_interval_hours * 3600):
            return self.update_available

        try:
            # Check GitHub API for latest release
            api_url = f"https://api.github.com/repos/{self.github_repo}/releases/latest"
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()

            release_data = response.json()
            self.latest_version = release_data.get("tag_name", "").lstrip("v")
            self.release_info = release_data

            # Compare versions (simple string comparison for now)
            if self._is_newer_version(self.latest_version, self.current_version):
                self.update_available = True
                print(f"Update available: {self.current_version} -> {self.latest_version}")

                from likepilot.core.notifications import notification_manager
                notification_manager.notify_system_error(
                    "update_available",
                    f"LikePilot {self.latest_version} is available (current: {self.current_version})"
                )

                if self.auto_install:
                    self.install_update()
            else:
                self.update_available = False

        except Exception as e:
            print(f"Update check failed: {e}")
            self.update_available = False

        self.last_check = current_time
        return self.update_available

    def install_update(self):
        """Refuse in-place updates until packages can be verified and applied atomically."""
        print(
            "Updater installation is disabled: downloaded archives are not yet "
            "signature-verified or safely staged. Update the installation manually."
        )
        return False

    def _is_newer_version(self, new_version, current_version):
        """Compare version strings"""
        try:
            # Simple version comparison (assumes semantic versioning)
            new_parts = [int(x) for x in new_version.split('.')]
            current_parts = [int(x) for x in current_version.split('.')]

            # Pad shorter version with zeros
            max_len = max(len(new_parts), len(current_parts))
            new_parts.extend([0] * (max_len - len(new_parts)))
            current_parts.extend([0] * (max_len - len(current_parts)))

            return new_parts > current_parts

        except Exception:
            # Fall back to string comparison
            return new_version > current_version

    def get_update_info(self):
        """Get information about available update"""
        if not self.update_available:
            return None

        return {
            "current_version": self.current_version,
            "latest_version": self.latest_version,
            "release_notes": self.release_info.get("body", "") if self.release_info else "",
            "release_date": self.release_info.get("published_at") if self.release_info else None,
            "download_url": self.release_info.get("html_url") if self.release_info else None
        }

    def schedule_update_check(self):
        """Schedule periodic update checks"""
        if not self.enabled:
            return

        import threading
        def check_loop():
            while True:
                self.check_for_updates()
                time.sleep(self.check_interval_hours * 3600)

        thread = threading.Thread(target=check_loop, daemon=True)
        thread.start()

# Global instance
auto_updater = AutoUpdater()