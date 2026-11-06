# LikePilot

LikePilot is a multi-platform automation and agent-management application built with Python. It connects engagement/task providers with supported social networks through configurable agents and a browser-based dashboard.

**LikePilot has one delivery model: a web application.** It runs as a Python server and is accessed through a normal browser. There is no desktop application, native window wrapper, or executable distribution.

The project is actively developed for educational, experimental, and software-development purposes. Integrations and workflows are evolving; not all functionality should be considered production-ready. Users are responsible for complying with connected services' terms and automating only accounts and environments they are authorized to use.

## Quick start

Requirements: Python 3.10 or newer and a supported Chrome/Chromium browser for browser-driven agent workflows.

```bash
git clone https://github.com/voidsgnl/LikePilot.git
cd LikePilot

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e .

cp .env.example .env
```

Edit `.env` and set a private dashboard password and a persistent `FLASK_SECRET_KEY`. Then start the application:

```bash
python farm.py
```

Open the login URL printed by the server (normally `http://127.0.0.1:5001/login`). Stop the server with Ctrl+C.

The `farm.py` command is a small compatibility launcher. The installed package also provides `python -m likepilot` and the `likepilot` command.

## Application structure

- `src/likepilot/core/` — runtime, configuration, persistence, browser lifecycle, and shared services.
- `src/likepilot/integrations/providers/` and `src/likepilot/integrations/networks/` — provider foundations/adapters and social-network action adapters. Existing behavior is preserved during the initial move and boundaries will be refined after integration tests.
- `src/likepilot/dashboard/` — Flask application, templates, static assets, and favicon resources.
- `src/likepilot/entrypoints/` — supported web-server entrypoint.
- `config/` — sanitized configuration examples.
- `data/` — runtime configuration, state, database, browser profiles, logs, diagnostics, backups, and temporary files.
- `docs/` — architecture, development, and user documentation.
- `tests/` — automated checks.

## Configuration and data

Runtime-generated files are stored under `data/`: configuration in `data/config/`, agent/statistics/timing state in `data/state/`, SQLite databases in `data/database/`, browser profiles in `data/profiles/`, logs in `data/logs/`, diagnostics in `data/diagnostics/`, backups in `data/backups/`, and transient updater/runtime files in `data/runtime/` or `data/tmp/`. On first access, LikePilot non-destructively migrates matching root-level legacy files and directories. If both legacy and destination copies exist, it preserves the legacy copy rather than overwriting either. Set `LIKEPILOT_DATA_DIR` to choose the runtime root; the same `data/` layout is used beneath it.

Do not expose the development server to an untrusted network. Configure unique dashboard credentials and a stable secret key before use.

## Project status

See [ROADMAP.md](ROADMAP.md) for verified progress and remaining work. The directory migration is being performed incrementally; the roadmap distinguishes completed structural changes from startup and integration checks that still need to pass.
