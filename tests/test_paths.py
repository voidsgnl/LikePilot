import os

from likepilot.core.paths import get_runtime_root, runtime_dir, runtime_path


def test_runtime_file_paths_use_data_categories(tmp_path, monkeypatch):
    monkeypatch.setenv("LIKEPILOT_DATA_DIR", str(tmp_path))

    assert runtime_path("config.json") == str(tmp_path / "data" / "config" / "config.json")
    assert runtime_path("agents.json") == str(tmp_path / "data" / "state" / "agents.json")
    assert runtime_path("likepilot.db") == str(tmp_path / "data" / "database" / "likepilot.db")
    assert runtime_path("runtime_port.txt") == str(tmp_path / "data" / "runtime" / "runtime_port.txt")


def test_tracked_runtime_file_is_copied_without_dirtying_checkout(tmp_path, monkeypatch):
    monkeypatch.setenv("LIKEPILOT_DATA_DIR", str(tmp_path))
    legacy = tmp_path / "config.json"
    expected = '{"browser":{"default":"firefox"}}'
    legacy.write_text(expected, encoding="utf-8")

    destination = runtime_path("config.json")

    assert open(destination, encoding="utf-8").read() == expected
    assert legacy.read_text(encoding="utf-8") == expected


def test_runtime_seed_fallback_survives_root_cleanup(tmp_path, monkeypatch):
    monkeypatch.setenv("LIKEPILOT_DATA_DIR", str(tmp_path))
    seed_dir = tmp_path / "legacy" / "runtime-seed"
    seed_dir.mkdir(parents=True)
    expected = '[{"name":"AGENT_01"}]'
    (seed_dir / "agents.json").write_text(expected, encoding="utf-8")

    destination = runtime_path("agents.json")

    assert open(destination, encoding="utf-8").read() == expected
    assert (seed_dir / "agents.json").read_text(encoding="utf-8") == expected


def test_runtime_file_collision_preserves_both_copies(tmp_path, monkeypatch):
    monkeypatch.setenv("LIKEPILOT_DATA_DIR", str(tmp_path))
    legacy = tmp_path / "agents.json"
    legacy.write_text('[{"name":"legacy"}]', encoding="utf-8")
    destination = tmp_path / "data" / "state" / "agents.json"
    destination.parent.mkdir(parents=True)
    destination.write_text('[{"name":"current"}]', encoding="utf-8")

    assert runtime_path("agents.json") == str(destination)
    assert legacy.read_text(encoding="utf-8") == '[{"name":"legacy"}]'
    assert destination.read_text(encoding="utf-8") == '[{"name":"current"}]'


def test_runtime_directory_migration_moves_existing_contents(tmp_path, monkeypatch):
    monkeypatch.setenv("LIKEPILOT_DATA_DIR", str(tmp_path))
    legacy = tmp_path / "logs"
    legacy.mkdir()
    (legacy / "latest.log").write_text("existing log", encoding="utf-8")

    destination = runtime_dir("logs")

    assert (tmp_path / "data" / "logs" / "latest.log").read_text(encoding="utf-8") == "existing log"
    assert destination == str(tmp_path / "data" / "logs")
    assert not legacy.exists()


def test_runtime_directory_merge_preserves_collisions(tmp_path, monkeypatch):
    monkeypatch.setenv("LIKEPILOT_DATA_DIR", str(tmp_path))
    legacy = tmp_path / "diagnostics"
    legacy.mkdir()
    (legacy / "old.html").write_text("legacy", encoding="utf-8")
    destination = tmp_path / "data" / "diagnostics"
    destination.mkdir(parents=True)
    (destination / "same.png").write_text("new", encoding="utf-8")
    (legacy / "same.png").write_text("old", encoding="utf-8")

    runtime_dir("diagnostics")

    assert (destination / "old.html").read_text(encoding="utf-8") == "legacy"
    assert (destination / "same.png").read_text(encoding="utf-8") == "new"
    assert (legacy / "same.png").read_text(encoding="utf-8") == "old"


def test_runtime_root_respects_explicit_data_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("LIKEPILOT_DATA_DIR", str(tmp_path / "custom"))
    assert get_runtime_root() == str((tmp_path / "custom").resolve())
    assert os.path.isdir(tmp_path / "custom")
