import os
from pathlib import Path


def get_runtime_root():
    override = os.getenv("LIKEPILOT_DATA_DIR")
    if override:
        data_root = Path(override).expanduser().resolve()
        data_root.mkdir(parents=True, exist_ok=True)
        return str(data_root)

    # Keep source-checkout data beside the repository during the package migration.
    source_root = Path(__file__).resolve().parents[3]
    if (source_root / "farm.py").is_file() or (source_root / "pyproject.toml").is_file():
        return str(source_root)

    # Non-editable installs use a stable per-user data directory.
    data_root = Path.home() / ".local" / "share" / "likepilot"
    data_root.mkdir(parents=True, exist_ok=True)
    return str(data_root)


def runtime_path(*parts):
    return os.path.join(get_runtime_root(), *parts)
