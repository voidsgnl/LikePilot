import os
import shutil

from core.paths import bundle_path, runtime_path


DEFAULT_ENV_EXAMPLE = """CHROME_PROFILE=Profile 1
DASHBOARD_USER=admin
DASHBOARD_PASS=change-me
CHROME_WINDOW_SIZE=1600,900
LIKE4LIKE_USERNAME=
LIKE4LIKE_PASSWORD=
KINGDOMLIKES_USERNAME=
KINGDOMLIKES_PASSWORD=
YOULIKEHITS_USERNAME=
YOULIKEHITS_PASSWORD=
"""


DEFAULT_README = """LikePilot Portable Runtime
==========================

This folder is the portable runtime used by the LikePilot desktop executable.

Expected files:
- LikePilot.exe or LikePilot Dashboard.exe
- .env.example
- optional .env
- optional likepilot.db
- profiles/
- logs/
- diagnostics/

Notes:
- profiles/ starts empty and will fill as Chrome sessions are created
- logs/ and diagnostics/ are created automatically
- copy .env.example to .env and set your own values before using automation
"""


def _copy_if_missing(source_path, target_path):
    if os.path.exists(target_path) or not os.path.exists(source_path):
        return False
    shutil.copy2(source_path, target_path)
    return True


def _write_if_missing(target_path, content):
    if os.path.exists(target_path):
        return False
    with open(target_path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return True


def ensure_portable_runtime():
    created = {"directories": [], "files": []}

    for folder_name in ("logs", "diagnostics", "profiles"):
        target_dir = runtime_path(folder_name)
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir, exist_ok=True)
            created["directories"].append(target_dir)

    readme_target = runtime_path("README.md")
    env_example_target = runtime_path(".env.example")

    if _copy_if_missing(bundle_path("README.md"), readme_target):
        created["files"].append(readme_target)
    elif _write_if_missing(readme_target, DEFAULT_README):
        created["files"].append(readme_target)

    if _copy_if_missing(bundle_path(".env.example"), env_example_target):
        created["files"].append(env_example_target)
    elif _write_if_missing(env_example_target, DEFAULT_ENV_EXAMPLE):
        created["files"].append(env_example_target)

    return created
