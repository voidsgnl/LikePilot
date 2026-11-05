import os
import sys
from pathlib import Path


def get_runtime_root():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)

    override = os.getenv("LIKEPILOT_DATA_DIR")
    if override:
        return str(Path(override).expanduser().resolve())

    # Source checkout: keep existing user data beside the repository files.
    source_root = Path(__file__).resolve().parents[3]
    if (source_root / "farm.py").is_file() or (source_root / "pyproject.toml").is_file():
        return str(source_root)

    # Non-editable installs use a stable per-user data directory.
    return str(Path.home() / ".local" / "share" / "likepilot")


def get_bundle_root():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return str(Path(__file__).resolve().parents[1])


def runtime_path(*parts):
    return os.path.join(get_runtime_root(), *parts)


def bundle_path(*parts):
    return os.path.join(get_bundle_root(), *parts)
