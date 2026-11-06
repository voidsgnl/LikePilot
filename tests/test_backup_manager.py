import json
import os
import sqlite3
import zipfile

import pytest

from likepilot.core import backup_manager as backup_module


def _create_database(path, value):
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS records (value TEXT)")
        conn.execute("INSERT INTO records (value) VALUES (?)", (value,))


def _manager():
    return backup_module.BackupManager.__new__(backup_module.BackupManager)


def test_backup_database_uses_consistent_sqlite_snapshot(tmp_path, monkeypatch):
    source_path = tmp_path / "live.db"
    _create_database(source_path, "committed")
    monkeypatch.setattr(backup_module, "runtime_path", lambda name: str(source_path))

    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    _manager()._backup_database(str(backup_dir))

    with sqlite3.connect(backup_dir / "likepilot.db") as conn:
        assert conn.execute("SELECT value FROM records").fetchone() == ("committed",)
        assert conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)


def test_restore_database_replaces_live_database_atomically(tmp_path, monkeypatch):
    live_path = tmp_path / "live.db"
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    backup_path = backup_dir / "likepilot.db"
    _create_database(live_path, "current")
    _create_database(backup_path, "restored")
    monkeypatch.setattr(backup_module, "runtime_path", lambda name: str(live_path))

    _manager()._restore_database(str(backup_dir))

    with sqlite3.connect(live_path) as conn:
        assert conn.execute("SELECT value FROM records").fetchone() == ("restored",)
        assert conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert not list(tmp_path.glob(".likepilot-restore-*.db"))


def test_restore_rejects_corrupt_database_without_replacing_live_data(tmp_path, monkeypatch):
    live_path = tmp_path / "live.db"
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    (backup_dir / "likepilot.db").write_text("not a sqlite database", encoding="utf-8")
    _create_database(live_path, "keep")
    monkeypatch.setattr(backup_module, "runtime_path", lambda name: str(live_path))

    with pytest.raises(sqlite3.DatabaseError):
        _manager()._restore_database(str(backup_dir))

    with sqlite3.connect(live_path) as conn:
        assert conn.execute("SELECT value FROM records").fetchone() == ("keep",)
    assert not list(tmp_path.glob(".likepilot-restore-*.db"))


def test_backup_archive_restores_database_config_and_logs(tmp_path, monkeypatch):
    data = tmp_path / "data"
    backup_dir = data / "backups"
    logs_dir = data / "logs"
    config_dir = data / "config"
    state_dir = data / "state"
    database_dir = data / "database"
    for directory in (backup_dir, logs_dir, config_dir, state_dir, database_dir):
        directory.mkdir(parents=True, exist_ok=True)

    paths = {
        ".env": config_dir / ".env",
        "config.json": config_dir / "config.json",
        "agents.json": state_dir / "agents.json",
        "stats.json": state_dir / "stats.json",
        "likepilot.db": database_dir / "likepilot.db",
    }
    paths[".env"].write_text("TOKEN=original\n", encoding="utf-8")
    paths["config.json"].write_text(json.dumps({"theme": "dark"}), encoding="utf-8")
    paths["agents.json"].write_text("[]", encoding="utf-8")
    paths["stats.json"].write_text("{}", encoding="utf-8")
    paths["credential.key"].write_text("test-encryption-key", encoding="utf-8")
    _create_database(paths["likepilot.db"], "before")
    (logs_dir / "app.log").write_text("original log\n", encoding="utf-8")

    monkeypatch.setattr(
        backup_module,
        "runtime_path",
        lambda name: str(paths[name]),
    )
    monkeypatch.setattr(backup_module, "runtime_dir", lambda name: str(logs_dir))

    manager = _manager()
    manager.enabled = True
    manager.backup_dir = str(backup_dir)
    manager.max_backups = 7
    manager.last_backup = 0

    archive_path = manager.create_backup("test")
    assert archive_path and os.path.isfile(archive_path)
    with zipfile.ZipFile(archive_path) as archive:
        assert set(archive.namelist()) >= {
            ".env", "config.json", "agents.json", "stats.json",
            "likepilot.db", "credential.key", "logs/app.log",
        }
        assert archive.testzip() is None

    paths[".env"].write_text("TOKEN=changed\n", encoding="utf-8")
    paths["config.json"].write_text(json.dumps({"theme": "light"}), encoding="utf-8")
    (logs_dir / "app.log").write_text("changed log\n", encoding="utf-8")
    (logs_dir / "new.log").write_text("new log\n", encoding="utf-8")
    with sqlite3.connect(paths["likepilot.db"]) as conn:
        conn.execute("DELETE FROM records")
        conn.execute("INSERT INTO records (value) VALUES ('after')")

    assert manager.restore_backup(archive_path) is True
    assert paths[".env"].read_text(encoding="utf-8") == "TOKEN=original\n"
    assert json.loads(paths["config.json"].read_text(encoding="utf-8")) == {"theme": "dark"}
    assert (logs_dir / "app.log").read_text(encoding="utf-8") == "original log\n"
    assert not (logs_dir / "new.log").exists()
    with sqlite3.connect(paths["likepilot.db"]) as conn:
        assert conn.execute("SELECT value FROM records").fetchone() == ("before",)


def test_restore_rejects_zip_path_traversal(tmp_path):
    archive_path = tmp_path / "malicious.zip"
    outside = tmp_path / "escaped.txt"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../escaped.txt", "unsafe")

    manager = _manager()
    manager.backup_dir = str(tmp_path / "backups")
    assert manager.restore_backup(str(archive_path)) is False
    assert not outside.exists()


def test_restore_validates_json_before_replacing_database(tmp_path, monkeypatch):
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    (backup_dir / "config.json").write_text("{invalid", encoding="utf-8")
    _create_database(backup_dir / "likepilot.db", "backup")
    live_path = tmp_path / "live.db"
    _create_database(live_path, "keep")
    monkeypatch.setattr(backup_module, "runtime_path", lambda name: str(live_path))

    assert _manager().restore_backup(str(backup_dir)) is False
    with sqlite3.connect(live_path) as conn:
        assert conn.execute("SELECT value FROM records").fetchone() == ("keep",)
