"""
LikePilot Backup System
Automatically backs up database and configuration files
"""
import os
import shutil
import json
import sqlite3
import time
import zipfile
from datetime import datetime
from likepilot.core.config import get_config_value
from likepilot.core.paths import get_runtime_root, runtime_dir, runtime_path

class BackupManager:
    def __init__(self):
        self.enabled = get_config_value("backup.enabled", True)
        self.backup_interval_hours = get_config_value("backup.interval_hours", 24)
        self.max_backups = get_config_value("backup.max_backups", 7)
        self.backup_path = get_config_value("backup.path", "backups")

        # Ensure backup directory exists
        self.backup_dir = (
            runtime_dir("backups")
            if self.backup_path == "backups"
            else os.path.abspath(os.path.join(get_runtime_root(), os.path.expanduser(self.backup_path)))
        )
        os.makedirs(self.backup_dir, exist_ok=True)

        self.last_backup = 0

    def should_backup(self):
        """Check if it's time for a backup"""
        if not self.enabled:
            return False

        current_time = time.time()
        return current_time - self.last_backup >= (self.backup_interval_hours * 3600)

    def create_backup(self, reason="scheduled"):
        """Create a backup of database and configuration"""
        if not self.enabled:
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"likepilot_backup_{timestamp}_{reason}"
            backup_path = os.path.join(self.backup_dir, backup_name)

            print(f"Creating backup: {backup_name}")

            # Create backup directory
            os.makedirs(backup_path, exist_ok=True)

            # Backup database
            self._backup_database(backup_path)

            # Backup configuration
            self._backup_config(backup_path)

            # Backup logs
            self._backup_logs(backup_path)

            # Create zip archive
            zip_path = self._create_zip_archive(backup_path, backup_name)

            # Clean up old backups
            self._cleanup_old_backups()

            # Update last backup time
            self.last_backup = time.time()

            print(f"Backup completed: {zip_path}")

            from likepilot.core.notifications import notification_manager
            notification_manager.notify_system_error(
                "backup_completed",
                f"LikePilot backup created: {backup_name}"
            )

            return zip_path

        except Exception as e:
            print(f"Backup failed: {e}")

            from likepilot.core.notifications import notification_manager
            notification_manager.notify_system_error(
                "backup_failed",
                f"LikePilot backup failed: {e}"
            )

            return None

    def restore_backup(self, backup_path):
        """Restore from a backup"""
        try:
            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"Backup not found: {backup_path}")

            print(f"Restoring from backup: {backup_path}")

            # If it's a zip file, extract it
            if backup_path.endswith('.zip'):
                extract_path = backup_path.replace('.zip', '_extracted')
                with zipfile.ZipFile(backup_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                backup_path = extract_path

            # Restore database
            self._restore_database(backup_path)

            # Restore configuration
            self._restore_config(backup_path)

            print("Backup restoration completed")

            from likepilot.core.notifications import notification_manager
            notification_manager.notify_system_error(
                "backup_restored",
                f"LikePilot backup restored from {backup_path}"
            )

            return True

        except Exception as e:
            print(f"Backup restoration failed: {e}")

            from likepilot.core.notifications import notification_manager
            notification_manager.notify_system_error(
                "restore_failed",
                f"LikePilot backup restoration failed: {e}"
            )

            return False

    def list_backups(self):
        """List available backups"""
        try:
            backups = []
            for item in os.listdir(self.backup_dir):
                if item.startswith("likepilot_backup_") and item.endswith(".zip"):
                    path = os.path.join(self.backup_dir, item)
                    stat = os.stat(path)
                    backups.append({
                        "name": item,
                        "path": path,
                        "size_mb": round(stat.st_size / (1024 * 1024), 2),
                        "created": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })

            return sorted(backups, key=lambda x: x["created"], reverse=True)

        except Exception as e:
            print(f"Failed to list backups: {e}")
            return []

    def _backup_database(self, backup_path):
        """Backup the SQLite database"""
        try:
            db_path = runtime_path("likepilot.db")
            if os.path.exists(db_path):
                backup_db_path = os.path.join(backup_path, "likepilot.db")
                shutil.copy2(db_path, backup_db_path)
                print("Database backup completed")
            else:
                print("Database file not found, skipping database backup")
        except Exception as e:
            print(f"Database backup failed: {e}")

    def _backup_config(self, backup_path):
        """Backup configuration files"""
        try:
            config_files = ["config.json", "agents.json", "stats.json"]

            for config_file in config_files:
                src_path = runtime_path(config_file)
                if os.path.exists(src_path):
                    dst_path = os.path.join(backup_path, config_file)
                    shutil.copy2(src_path, dst_path)

            print("Configuration backup completed")
        except Exception as e:
            print(f"Configuration backup failed: {e}")

    def _backup_logs(self, backup_path):
        """Backup log files"""
        try:
            logs_dir = runtime_dir("logs")
            if os.path.exists(logs_dir):
                backup_logs_dir = os.path.join(backup_path, "logs")
                shutil.copytree(logs_dir, backup_logs_dir,
                              ignore=shutil.ignore_patterns('*.tmp'))
                print("Logs backup completed")
        except Exception as e:
            print(f"Logs backup failed: {e}")

    def _create_zip_archive(self, backup_path, backup_name):
        """Create a zip archive of the backup"""
        try:
            zip_path = os.path.join(self.backup_dir, f"{backup_name}.zip")

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(backup_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, backup_path)
                        zipf.write(file_path, arcname)

            # Remove the uncompressed backup directory
            shutil.rmtree(backup_path)

            return zip_path

        except Exception as e:
            print(f"Zip archive creation failed: {e}")
            return backup_path

    def _restore_database(self, backup_path):
        """Restore the database from backup"""
        try:
            backup_db_path = os.path.join(backup_path, "likepilot.db")
            if os.path.exists(backup_db_path):
                db_path = runtime_path("likepilot.db")
                shutil.copy2(backup_db_path, db_path)
                print("Database restoration completed")
        except Exception as e:
            print(f"Database restoration failed: {e}")

    def _restore_config(self, backup_path):
        """Restore configuration files from backup"""
        try:
            config_files = ["config.json", "agents.json", "stats.json"]

            for config_file in config_files:
                backup_config_path = os.path.join(backup_path, config_file)
                if os.path.exists(backup_config_path):
                    config_path = runtime_path(config_file)
                    shutil.copy2(backup_config_path, config_path)

            print("Configuration restoration completed")
        except Exception as e:
            print(f"Configuration restoration failed: {e}")

    def _cleanup_old_backups(self):
        """Remove old backups to stay within max_backups limit"""
        try:
            backups = self.list_backups()

            if len(backups) > self.max_backups:
                backups_to_remove = backups[self.max_backups:]

                for backup in backups_to_remove:
                    try:
                        os.remove(backup["path"])
                        print(f"Removed old backup: {backup['name']}")
                    except Exception as e:
                        print(f"Failed to remove old backup {backup['name']}: {e}")

        except Exception as e:
            print(f"Backup cleanup failed: {e}")

# Global instance
backup_manager = BackupManager()