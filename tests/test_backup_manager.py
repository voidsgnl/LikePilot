import sqlite3

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
