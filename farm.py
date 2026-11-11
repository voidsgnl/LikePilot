"""Compatibility launcher for the LikePilot web application."""
from pathlib import Path
import sys

SOURCE_ROOT = Path(__file__).resolve().parent / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))


def main():
    from likepilot.entrypoints.server import main as run_server

    run_server()


if __name__ == "__main__":
    main()
