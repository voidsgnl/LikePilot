"""Centralized runtime paths and non-destructive legacy-data migration."""
import os
import shutil
from pathlib import Path


_DATA_FILES = {
    ".env": ("config", ".env"),
    "config.json": ("config", "config.json"),
    "agents.json": ("state", "agents.json"),
    "stats.json": ("state", "stats.json"),
    "timing_data.json": ("state", "timing_data.json"),
    "likepilot.db": ("database", "likepilot.db"),
    "likeit.db": ("database", "likeit.db"),
    "runtime_port.txt": ("runtime", "runtime_port.txt"),
    "update.zip": ("tmp", "update.zip"),
    "credential.key": ("config", "credential.key"),
    "dashboard-password": ("config", "dashboard-password"),
    "dashboard-session.key": ("config", "dashboard-session.key"),
}
_TRACKED_LEGACY_FILES = {"config.json", "agents.json", "stats.json"}
_DATA_DIRS = {
    "profiles": "profiles",
    "logs": "logs",
    "diagnostics": "diagnostics",
    "backups": "backups",
    "update_temp": "tmp/update_temp",
}


def _restrict_directory_permissions(path):
    """Keep private runtime data directories accessible only to their owner."""
    if os.name == "posix":
        try:
            os.chmod(path, 0o700)
        except OSError:
            pass


def get_runtime_root():
    override = os.getenv("LIKEPILOT_DATA_DIR")
    if override:
        data_root = Path(override).expanduser().resolve()
        data_root.mkdir(parents=True, exist_ok=True)
        return str(data_root)

    source_root = Path(__file__).resolve().parents[3]
    if (source_root / "farm.py").is_file() or (source_root / "pyproject.toml").is_file():
        return str(source_root)

    data_root = Path.home() / ".local" / "share" / "likepilot"
    data_root.mkdir(parents=True, exist_ok=True)
    return str(data_root)


def _merge_legacy_directory(legacy, destination):
    """Move non-conflicting legacy entries; leave collisions untouched."""
    legacy = Path(legacy)
    destination = Path(destination)
    if not legacy.is_dir():
        return
    destination.mkdir(parents=True, exist_ok=True)
    for item in legacy.iterdir():
        target = destination / item.name
        if not target.exists():
            shutil.move(str(item), str(target))
        elif item.is_dir() and target.is_dir():
            _merge_legacy_directory(item, target)
            try:
                item.rmdir()
            except OSError:
                pass
    try:
        legacy.rmdir()
    except OSError:
        # Empty or conflicting legacy parents are deliberately preserved.
        pass


def runtime_dir(name):
    """Return a data-directory path, migrating legacy root contents once."""
    root = Path(get_runtime_root())
    relative = _DATA_DIRS.get(name, name)
    destination = root / "data" / relative
    legacy = root / name
    if legacy.resolve() != destination.resolve() and legacy.exists():
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.replace(legacy, destination)
            except OSError:
                _merge_legacy_directory(legacy, destination)
        elif legacy.is_dir():
            _merge_legacy_directory(legacy, destination)
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    _restrict_directory_permissions(destination)
    return str(destination)


def runtime_path(*parts):
    """Resolve runtime files under data/ and migrate matching legacy files safely."""
    if not parts:
        return get_runtime_root()
    root = Path(get_runtime_root())
    first = str(parts[0])
    mapped = _DATA_FILES.get(first)
    if mapped:
        destination = root / "data" / mapped[0] / mapped[1]
        legacy = root / first
        if not legacy.exists() and first in _TRACKED_LEGACY_FILES:
            legacy = root / "legacy" / "runtime-seed" / first
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        _restrict_directory_permissions(destination.parent)
        if legacy.exists() and not destination.exists() and legacy.is_file():
            if first in _TRACKED_LEGACY_FILES:
                # These compatibility seeds are tracked by Git. Copy them so
                # upgrading a checkout does not create tracked-file deletions.
                shutil.copy2(legacy, destination)
            else:
                try:
                    os.replace(legacy, destination)
                except OSError:
                    shutil.copy2(legacy, destination)
        return str(destination.joinpath(*map(str, parts[1:])))

    if first in _DATA_DIRS:
        base = Path(runtime_dir(first))
        return str(base.joinpath(*map(str, parts[1:])))
    return str(root.joinpath(*map(str, parts)))
