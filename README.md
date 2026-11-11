# LikePilot

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6%2B-F7DF1E?logo=javascript&logoColor=111111)
![HTML5](https://img.shields.io/badge/HTML5-dashboard-E34F26?logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-styling-1572B6?logo=css3&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-2ea44f)

LikePilot is a browser-based automation and agent-management application. It provides a dashboard for managing agents, connecting supported providers and platforms, and monitoring browser-driven workflows.

> **Pre-release — v0.1.0.** LikePilot is under development and may change as features and integrations are refined.

## Features

- Manage and monitor automation agents.
- Configure supported task providers and social-platform integrations.
- Run browser-driven workflows with Chrome or Chromium.
- Monitor activity, analytics, logs, and diagnostics.
- Pause tasks for manual social-platform sign-in, then resume when the session is detected.

## Requirements

- Python 3.10 or newer
- pip and Python virtual-environment support
- Google Chrome or compatible Chromium for browser automation

## Quick start

Clone the repository:

```bash
git clone https://github.com/voidsgnl/LikePilot.git
cd LikePilot
```

Create and activate a virtual environment, then install:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Create the runtime configuration:

```bash
mkdir -p data/config
cp .env.example data/config/.env
```

Set a unique `DASHBOARD_PASS` in `data/config/.env`. It must contain 1–64 numeric digits. Then start LikePilot:

```bash
python farm.py
```

Open the dashboard URL printed in the terminal. By default, it uses `http://127.0.0.1:5001/login`.

## Security

LikePilot can handle account credentials, browser sessions, and other sensitive runtime data. Keep the dashboard bound to `127.0.0.1` unless you have separately secured the deployment. The numeric vault is intended as a local convenience gate, not strong authentication for an internet-facing service. Never commit passwords, tokens, cookies, browser profiles, or runtime data.

Read [SECURITY.md](SECURITY.md) before reporting a vulnerability.

## Documentation

- [Quick start and upgrade notes](docs/user-guide/quickstart.md)
- [Dashboard authentication and network security](docs/user-guide/dashboard-security.md)
- [Credential storage](docs/user-guide/credential-storage.md)
- [Integration matrix](docs/architecture/integration-matrix.md)
- [Persistence and runtime data](docs/architecture/persistence.md)
- [Development setup](docs/development/setup.md)
- [Contributing](CONTRIBUTING.md)

## License

MIT — see [LICENSE](LICENSE).
