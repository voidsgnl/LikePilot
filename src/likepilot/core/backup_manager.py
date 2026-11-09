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
import tempfile
from pathlib import PurePosixPath
from datetime import datetime
from likepilot.core.config import get_config_value
from likepilot.core.paths import get_runtime_root, runtime_dir, runtime_path

class BackupManager:
    def __init__(self):
        self.enabled = get_config_value("backup.enabled", True)
        self.backup_interval_hours = get_config_value("backup.interval_hours", 24)
        self.max_backups = get_config_value("backup.max_backups", 7)
        self.backup_path = get_config_value("backup.path", "backups")

        # Backup archives contain encryption keys and authentication secrets.
        self.backup_dir = (
            runtime_dir("backups")
            if self.backup_path == "backups"
            else os.path.abspath(os.path.join(get_runtime_root(), os.path.expanduser(self.backup_path)))
        )
        os.makedirs(self.backup_dir, mode=0o700, exist_ok=True)
        if os.name == "posix":
            try:
                os.chmod(self.backup_dir, 0o700)
            except OSError:
                pass

        self.last_backup = 0

    def should_backup(self):
        """Check if it's time for a backup"""
        if not self.enabled:
            return False

        current_time = time.time()
        return current_time - self.last_backup >= (self.backup_interval_hours * 3600)

    def create_backup(self, reason="scheduled"):
        """Create a complete backup archive or fail without publishing a partial one."""
        if not self.enabled:
            return None

        os.makedirs(self.backup_dir, mode=0o700, exist_ok=True)
        if os.name == "posix":
            try:
                os.chmod(self.backup_dir, 0o700)
            except OSError:
                pass

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_reason = "".join(
            char if char.isalnum() or char in "-_" else "_"
            for char in str(reason)
        ).strip("_") or "manual"
        backup_name = f"likepilot_backup_{timestamp}_{safe_reason}"
        staging_path = tempfile.mkdtemp(prefix=f".{backup_name}-", dir=self.backup_dir)
        zip_path = os.path.join(self.backup_dir, f"{backup_name}.zip")
        temporary_zip = f"{zip_path}.tmp"

        try:
            self._backup_database(staging_path)
            self._backup_config(staging_path)
            self._backup_logs(staging_path)
            self._create_zip_archive(staging_path, temporary_zip)
            with zipfile.ZipFile(temporary_zip, "r") as archive:
                bad_member = archive.testzip()
                if bad_member:
                    raise zipfile.BadZipFile(f"Archive verification failed at {bad_member}")
            if os.name == "posix":
                os.chmod(temporary_zip, 0o600)
            os.replace(temporary_zip, zip_path)
            self._cleanup_old_backups()
            self.last_backup = time.time()

            from likepilot.core.notifications import notification_manager
            notification_manager.notify_system_error(
                "backup_completed",
                f"LikePilot backup created: {backup_name}"
            )
            return zip_path
        except Exception as error:
            print(f"Backup failed: {error}")
            try:
                from likepilot.core.notifications import notification_manager
                notification_manager.notify_system_error(
                    "backup_failed",
                    f"LikePilot backup failed: {error}"
                )
            except Exception:
                pass
            return None
        finally:
            shutil.rmtree(staging_path, ignore_errors=True)
            if os.path.exists(temporary_zip):
                os.remove(temporary_zip)

    def restore_backup(self, backup_path):
        """Restore a validated backup; stop the server and agents before calling."""
        extract_context = None
        try:
            if not os.path.exists(backup_path) or not (os.path.isfile(backup_path) or os.path.isdir(backup_path)):
                raise FileNotFoundError(f"Backup not found: {backup_path}")

            if os.path.isfile(backup_path) and zipfile.is_zipfile(backup_path):
                extract_context = tempfile.TemporaryDirectory(prefix="likepilot-restore-")
                with zipfile.ZipFile(backup_path, "r") as archive:
                    self._validate_archive_members(archive)
                    archive.extractall(extract_context.name)
                source_path = extract_context.name
            else:
                source_path = backup_path

            self._validate_backup_directory(source_path)
            self._restore_database(source_path)
            self._restore_config(source_path)
            self._restore_logs(source_path)

            from likepilot.core.notifications import notification_manager
            notification_manager.notify_system_error(
                "backup_restored",
                f"LikePilot backup restored from {backup_path}"
            )
            return True
        except Exception as error:
            print(f"Backup restoration failed: {error}")
            try:
                from likepilot.core.notifications import notification_manager
                notification_manager.notify_system_error(
                    "restore_failed",
                    f"LikePilot backup restoration failed: {error}"
                )
            except Exception:
                pass
            return False
        finally:
            if extract_context is not None:
                extract_context.cleanup()

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
        """Create a consistent SQLite snapshot, including committed WAL content."""
        db_path = runtime_path("likepilot.db")
        if not os.path.exists(db_path):
            print("Database file not found, skipping database backup")
            return

        backup_db_path = os.path.join(backup_path, "likepilot.db")
        source = sqlite3.connect(db_path, timeout=30)
        destination = sqlite3.connect(backup_db_path)
        try:
            source.backup(destination)
            result = destination.execute("PRAGMA integrity_check").fetchone()
            if not result or result[0] != "ok":
                raise sqlite3.DatabaseError(f"Backup database integrity check failed: {result}")
        finally:
            destination.close()
            source.close()
        print("Database backup completed")

    def _backup_config(self, backup_path):
        """Copy supported configuration/state files; fail the backup on I/O errors."""
        for config_file in (".env", "credential.key", "dashboard-password", "dashboard-session.key", "config.json", "agents.json", "stats.json"):
            source = runtime_path(config_file)
            if os.path.isfile(source):
                shutil.copy2(source, os.path.join(backup_path, config_file))

    def _backup_logs(self, backup_path):
        """Include runtime logs when present."""
        logs_dir = runtime_dir("logs")
        if os.path.isdir(logs_dir):
            shutil.copytree(
                logs_dir,
                os.path.join(backup_path, "logs"),
                ignore=shutil.ignore_patterns("*.tmp"),
            )

    def _create_zip_archive(self, backup_path, zip_path):
        """Write an archive to the supplied temporary path."""
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for root, _, files in os.walk(backup_path):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    archive_name = os.path.relpath(file_path, backup_path).replace(os.sep, "/")
                    archive.write(file_path, archive_name)
        return zip_path

    def _restore_database(self, backup_path):
        """Validate and atomically restore SQLite data.

        Stop the LikePilot server and agent workers before restoring so no
        process continues writing to the previous database file.
        """
        backup_db_path = os.path.join(backup_path, "likepilot.db")
        if not os.path.isfile(backup_db_path):
            return

        db_path = runtime_path("likepilot.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=".likepilot-restore-",
            suffix=".db",
            dir=os.path.dirname(db_path),
        )
        os.close(descriptor)

        source = destination = None
        try:
            source = sqlite3.connect(
                f"file:{os.path.abspath(backup_db_path)}?mode=ro",
                uri=True,
                timeout=30,
            )
            destination = sqlite3.connect(temporary_path)
            source.backup(destination)
            result = destination.execute("PRAGMA integrity_check").fetchone()
            if not result or result[0] != "ok":
                raise sqlite3.DatabaseError(f"Restore database integrity check failed: {result}")
            destination.close()
            destination = None
            source.close()
            source = None
            os.replace(temporary_path, db_path)
            # A stale WAL/SHM belongs to the previous database and must not be
            # replayed against the restored file. The application must be stopped.
            for suffix in ("-wal", "-shm"):
                sidecar = db_path + suffix
                if os.path.exists(sidecar):
                    os.remove(sidecar)
        finally:
            if destination is not None:
                destination.close()
            if source is not None:
                source.close()
            if os.path.exists(temporary_path):
                os.remove(temporary_path)

    def _restore_config(self, backup_path):
        """Validate and atomically replace backed-up configuration/state files."""
        staged = []
        try:
            for filename in (".env", "credential.key", "dashboard-password", "dashboard-session.key", "config.json", "agents.json", "stats.json"):
                source = os.path.join(backup_path, filename)
                if not os.path.isfile(source):
                    continue
                if filename.endswith(".json"):
                    with open(source, "r", encoding="utf-8") as stream:
                        json.load(stream)

                destination = runtime_path(filename)
                os.makedirs(os.path.dirname(destination), exist_ok=True)
                descriptor, temporary = tempfile.mkstemp(
                    prefix=f".{filename}.restore-",
                    dir=os.path.dirname(destination),
                )
                os.close(descriptor)
                shutil.copy2(source, temporary)
                staged.append((temporary, destination))

            for temporary, destination in staged:
                os.replace(temporary, destination)
                if os.name == "posix" and os.path.basename(destination) in {".env", "credential.key", "dashboard-password", "dashboard-session.key"}:
                    try:
                        os.chmod(destination, 0o600)
                    except OSError:
                        pass
        finally:
            for temporary, _ in staged:
                if os.path.exists(temporary):
                    os.remove(temporary)

    @staticmethod
    def _validate_archive_members(archive):
        """Reject archive paths that could escape the extraction directory."""
        allowed_files = {".env", "credential.key", "dashboard-password", "dashboard-session.key", "config.json", "agents.json", "stats.json", "likepilot.db"}
        for member in archive.infolist():
            name = member.filename
            path = PurePosixPath(name)
            if (
                not name
                or "\\" in name
                or path.is_absolute()
                or any(part in ("", ".", "..") for part in path.parts)
                or not (name.rstrip("/") in allowed_files or path.parts[0] == "logs")
            ):
                raise zipfile.BadZipFile(f"Unsupported backup member path: {name}")
            unix_mode = member.external_attr >> 16
            if unix_mode and (unix_mode & 0o170000) == 0o120000:
                raise zipfile.BadZipFile(f"Symbolic links are not allowed: {name}")

    @staticmethod
    def _validate_backup_directory(backup_path):
        """Validate supported backup files before modifying runtime data."""
        allowed_files = {".env", "credential.key", "dashboard-password", "dashboard-session.key", "config.json", "agents.json", "stats.json", "likepilot.db"}
        entries = set(os.listdir(backup_path))
        unsupported = entries - allowed_files - {"logs"}
        if unsupported:
            raise ValueError(f"Unsupported backup entries: {sorted(unsupported)}")
        for filename in ("config.json", "agents.json", "stats.json"):
            path = os.path.join(backup_path, filename)
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as stream:
                    json.load(stream)
        database = os.path.join(backup_path, "likepilot.db")
        if os.path.isfile(database):
            connection = sqlite3.connect(f"file:{os.path.abspath(database)}?mode=ro", uri=True)
            try:
                result = connection.execute("PRAGMA integrity_check").fetchone()
                if not result or result[0] != "ok":
                    raise sqlite3.DatabaseError(f"Backup database integrity check failed: {result}")
            finally:
                connection.close()
        logs = os.path.join(backup_path, "logs")
        if os.path.exists(logs) and not os.path.isdir(logs):
            raise ValueError("Backup logs entry must be a directory")

    def _restore_logs(self, backup_path):
        """Replace runtime logs from the backup using a staged directory."""
        source = os.path.join(backup_path, "logs")
        if not os.path.isdir(source):
            return

        destination = runtime_dir("logs")
        parent = os.path.dirname(destination)
        staged = tempfile.mkdtemp(prefix=".logs-restore-", dir=parent)
        previous = None
        try:
            shutil.rmtree(staged)
            shutil.copytree(source, staged)
            if os.path.exists(destination):
                previous = tempfile.mkdtemp(prefix=".logs-previous-", dir=parent)
                os.rmdir(previous)
                os.replace(destination, previous)
            try:
                os.replace(staged, destination)
            except Exception:
                if previous and os.path.exists(previous):
                    os.replace(previous, destination)
                    previous = None
                raise
            if previous:
                shutil.rmtree(previous)
                previous = None
        finally:
            if os.path.exists(staged):
                shutil.rmtree(staged, ignore_errors=True)
            if previous and os.path.exists(previous):
                shutil.rmtree(previous, ignore_errors=True)

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