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
- `src/likepilot/integrations/adapters/` — current provider adapters. Their provider/network coupling is preserved during the initial move and will be refined after behavior tests.
- `src/likepilot/dashboard/` — Flask application, templates, static assets, and favicon resources.
- `src/likepilot/entrypoints/` — supported web-server entrypoint.
- `config/` — sanitized configuration examples.
- `data/` — reserved for runtime data as its migration is completed; existing user data is not moved automatically.
- `docs/` — architecture, development, and user documentation.
- `tests/` — automated checks.

## Configuration and data

The application currently reads `config.json`, `.env`, agent state, and other runtime files from the repository/runtime root. Existing files are intentionally preserved during the source-layout migration. A later data-path migration will move runtime-generated data into `data/` with compatibility handling; do not move or delete existing databases, profiles, logs, or configuration files manually as part of this code migration.

Do not expose the development server to an untrusted network. Configure unique dashboard credentials and a stable secret key before use.

## Project status

See [ROADMAP.md](ROADMAP.md) for verified progress and remaining work. The directory migration is being performed incrementally; the roadmap distinguishes completed structural changes from startup and integration checks that still need to pass.
