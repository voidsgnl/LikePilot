"""Compatibility launcher for the LikePilot web application."""
from pathlib import Path
import sys

SOURCE_ROOT = Path(__file__).resolve().parent / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from likepilot.entrypoints.server import main


if __name__ == "__main__":
    main()
