"""
LikePilot Auto-Updater
Checks for updates and applies them automatically
"""
import requests
import json
import os
import subprocess
import time
from datetime import datetime
from likepilot.core.config import get_config_value
from likepilot.core.paths import get_runtime_root, runtime_dir, runtime_path

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
        """Install the available update"""
        if not self.update_available or not self.release_info:
            return False

        try:
            print(f"Installing update to version {self.latest_version}...")

            # Download the update
            download_url = None
            for asset in self.release_info.get("assets", []):
                if "likepilot" in asset["name"].lower() and asset["name"].endswith(".zip"):
                    download_url = asset["browser_download_url"]
                    break

            if not download_url:
                print("No suitable update package found")
                return False

            # Download and extract update
            response = requests.get(download_url, timeout=60)
            response.raise_for_status()

            update_zip_path = runtime_path("update.zip")
            with open(update_zip_path, 'wb') as f:
                f.write(response.content)

            # Extract update
            import zipfile
            update_dir = runtime_dir("update_temp")

            with zipfile.ZipFile(update_zip_path, 'r') as zip_ref:
                zip_ref.extractall(update_dir)

            # Backup current version
            self._backup_current_version()

            # Apply update
            self._apply_update_files(update_dir)

            # Clean up
            os.remove(update_zip_path)
            import shutil
            shutil.rmtree(update_dir)

            # Update version
            self.current_version = self.latest_version
            self.update_available = False

            print(f"Successfully updated to version {self.latest_version}")

            from likepilot.core.notifications import notification_manager
            notification_manager.notify_system_error(
                "update_installed",
                f"LikePilot successfully updated to {self.latest_version}"
            )

            return True

        except Exception as e:
            print(f"Update installation failed: {e}")

            from likepilot.core.notifications import notification_manager
            notification_manager.notify_system_error(
                "update_failed",
                f"Failed to install update: {e}"
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

    def _backup_current_version(self):
        """Create backup of current version"""
        try:
            import shutil
            backup_dir = os.path.join(runtime_dir("backups"), f"updater_{self.current_version}_{int(time.time())}")
            shutil.copytree(get_runtime_root(), backup_dir,
                          ignore=shutil.ignore_patterns('backup_*', 'update_temp', '__pycache__', '*.pyc'))
            print(f"Backup created: {backup_dir}")
        except Exception as e:
            print(f"Backup failed: {e}")

    def _apply_update_files(self, update_dir):
        """Apply update files to current installation"""
        try:
            import shutil

            # Get list of files to update
            for root, dirs, files in os.walk(update_dir):
                # Skip certain directories
                dirs[:] = [d for d in dirs if d not in ['__pycache__', 'backup_*', 'update_temp']]

                for file in files:
                    if file.endswith(('.pyc', '.pyo')):
                        continue

                    source_path = os.path.join(root, file)
                    relative_path = os.path.relpath(source_path, update_dir)
                    target_path = os.path.join(get_runtime_root(), relative_path)

                    # Create target directory if needed
                    target_dir = os.path.dirname(target_path)
                    os.makedirs(target_dir, exist_ok=True)

                    # Copy file
                    shutil.copy2(source_path, target_path)
                    print(f"Updated: {relative_path}")

        except Exception as e:
            raise Exception(f"Failed to apply update files: {e}")

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