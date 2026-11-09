# LikePilot

LikePilot is a browser-based automation and agent-management application. It provides a web dashboard for configuring agents, managing supported providers and platforms, monitoring activity, and operating browser-driven workflows.

The application is delivered as a **Python web service with a browser dashboard**. It does not currently ship as a native desktop application or standalone executable.

> **Project status:** Active development. Features, integrations, and operational workflows are evolving. Do not assume that every integration is production-ready. Review the security and deployment guidance before exposing an instance beyond localhost.

## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Run LikePilot](#run-likepilot)
- [Runtime data](#runtime-data)
- [Development](#development)
- [Security and deployment](#security-and-deployment)
- [Project structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Project status and contribution](#project-status-and-contribution)
- [License](#license)

## Features

The application is organized around a central dashboard and agent workspace:

- **Agent management** — create, configure, monitor, and operate automation agents.
- **Provider integrations** — connect supported task or engagement providers.
- **Platform integrations** — use supported social-network adapters through configured agents.
- **Operations** — inspect runtime logs, database information, and diagnostics.
- **Analytics** — review available activity and performance data.
- **Browser automation** — run supported workflows through Chrome/Chromium and Selenium.
- **Persistent local state** — keep configuration, database state, browser profiles, logs, and backups in a dedicated runtime data directory.

Available capabilities depend on the integrations and workflows implemented in the current version. Consult the application and project roadmap rather than assuming every area supports every provider or platform.

## Requirements

- Python **3.10 or newer**.
- pip and Python virtual-environment support.
- Google Chrome or a compatible Chromium browser for browser-driven workflows.
- An operating-system environment supported by the installed browser and Selenium dependencies.

The project declares its Python dependencies in pyproject.toml.

## Installation

Clone the repository and enter the project directory:

~~~bash
git clone https://github.com/voidsgnl/LikePilot.git
cd LikePilot
~~~

Create and activate a virtual environment.

**Linux / macOS**

~~~bash
python3 -m venv .venv
source .venv/bin/activate
~~~

**Windows PowerShell**

~~~powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
~~~

Install LikePilot in editable mode:

~~~bash
python -m pip install --upgrade pip
python -m pip install -e .
~~~

Create the local environment file.

**Linux / macOS**

~~~bash
cp .env.example .env
~~~

**Windows PowerShell**

~~~powershell
Copy-Item .env.example .env
~~~

Review the values in .env before starting the application.

## Configuration

LikePilot reads environment settings from the runtime .env file and the process environment. The example file documents the supported startup settings:

| Variable | Default | Description |
| --- | --- | --- |
| DASHBOARD_HOST | 127.0.0.1 | Network interface used by the web server. |
| DASHBOARD_PORT | 5001 | Preferred local dashboard port. If unavailable, startup checks subsequent ports. |
| DASHBOARD_USER | admin | Dashboard login username. |
| DASHBOARD_PASS | Generated when unset | Dashboard login password. A unique password is initialized and written to the runtime password file when no password is configured. |
| FLASK_SECRET_KEY | Generated and persisted when unset | Secret used to sign Flask sessions. Configure a stable, private value for persistent deployments. |
| DASHBOARD_COOKIE_SECURE | Application default | Set to true when the dashboard is served over HTTPS and secure cookies are required. |

For a local installation, the default host binds the service to loopback so it is not directly reachable from other machines.

### Credentials and secrets

- Never commit .env, passwords, API tokens, cookies, browser profiles, or runtime databases.
- Use unique dashboard credentials; do not retain shared or default credentials in a deployed environment.
- Keep the generated credential-encryption key at data/config/credential.key protected and include it in secure backups. Losing it may make stored credentials unrecoverable.
- Protect the runtime password file and all backup copies with restrictive filesystem permissions.
- Rotate credentials immediately if they may have been exposed.

## Run LikePilot

Start the application from the repository root:

~~~bash
python farm.py
~~~

The server prints the dashboard login URL and the location of its runtime port file. With the default configuration, open:

~~~text
http://127.0.0.1:5001/login
~~~

The root farm.py file is the compatibility launcher. The package also supports these equivalent entry points after installation:

~~~bash
python -m likepilot
~~~

~~~bash
likepilot
~~~

Stop the foreground server with **Ctrl+C**.

## Runtime data

Application-generated data is stored separately from tracked source code. By default, LikePilot uses the repository's data/ directory.

| Location | Purpose |
| --- | --- |
| data/config/ | Runtime configuration, dashboard password, and credential-encryption key. |
| data/state/ | Agent state, statistics, and timing information. |
| data/database/ | SQLite databases. |
| data/profiles/ | Browser profiles and session data. |
| data/logs/ | Application and agent logs. |
| data/diagnostics/ | Diagnostic output and captures. |
| data/backups/ | Application backups. |
| data/runtime/ | Runtime metadata and updater files. |
| data/tmp/ | Temporary files. |

Set LIKEPILOT_DATA_DIR to use a different runtime root. The same directory layout is created beneath the selected path.

On startup, LikePilot includes non-destructive migration handling for supported legacy runtime files and directories. Existing destination files are not intentionally overwritten during migration. Back up the old runtime directory before upgrading, and verify that the application can read migrated data before removing legacy copies.

**Back up the complete runtime data directory**, especially the database, configuration, and credential-encryption key. Store backups securely; they may contain sensitive account and session information.

## Development

Install the development dependencies:

~~~bash
python -m pip install -e ".[dev]"
~~~

Run the automated test suite:

~~~bash
python -m pytest
~~~

Run Ruff when making Python changes:

~~~bash
ruff check .
~~~

The project uses a src/ package layout. Run commands from the repository root with the project installed in the active virtual environment.

Before submitting a change:

1. Keep changes focused and consistent with existing package boundaries.
2. Add or update tests for changed behaviour.
3. Avoid committing runtime data, secrets, local browser profiles, or generated artifacts.
4. Run the relevant tests and linters.
5. Update documentation when setup, configuration, or user-facing behaviour changes.

## Security and deployment

LikePilot automates browser workflows and can store credentials, session data, and account-related information. Treat its runtime directory and dashboard as sensitive.

For local use, keep DASHBOARD_HOST=127.0.0.1. Do not bind the development server to a public interface or expose it directly to the internet.

A production deployment requires an appropriately secured hosting environment and additional operational controls, including:

- HTTPS termination through a properly configured reverse proxy.
- Strong, unique dashboard credentials and a persistent secret key.
- Secure cookie settings when HTTPS is enabled.
- Network access controls and firewall rules.
- Restricted filesystem permissions for runtime data and backups.
- Encrypted, tested backups and a recovery procedure.
- Monitoring, log retention, dependency updates, and incident response procedures.
- Verification that each connected provider and platform permits the intended automation.

The built-in server is intended for straightforward local operation. **This README does not certify the application as production-hardened.** Complete a security review and deployment validation before using it in a production or internet-facing environment.

Use LikePilot only with accounts, systems, and data you are authorized to access. You are responsible for complying with the terms, policies, and applicable laws governing connected services.

## Project structure

~~~text
LikePilot/
├── src/
│   └── likepilot/
│       ├── core/                 # Runtime, configuration, persistence, shared services
│       ├── integrations/
│       │   ├── providers/        # Provider adapters and foundations
│       │   └── networks/         # Platform and social-network adapters
│       ├── dashboard/            # Flask app, templates, static assets
│       └── entrypoints/          # Web-server entry point
├── config/                       # Sanitized configuration examples
├── data/                         # Local runtime data
├── docs/                         # Additional project documentation
├── legacy/runtime-seed/          # First-run compatibility seed data
├── tests/                        # Automated tests
├── farm.py                       # Compatibility launcher
├── pyproject.toml                # Package metadata and dependencies
├── requirements.txt              # Editable project install
└── .env.example                  # Environment configuration template
~~~

## Troubleshooting

### The dashboard does not open

- Check the startup output for the actual URL and selected port.
- If the preferred port is occupied, LikePilot may select a subsequent available port.
- Confirm that the process is still running and that local firewall rules allow loopback traffic.

### Browser automation cannot start

- Confirm that Chrome or Chromium is installed.
- Check that the browser can start under the same user account running LikePilot.
- Review the agent and runtime logs for Selenium or browser-driver errors.

### Stored credentials cannot be decrypted

- Confirm that the original data/config/credential.key is present.
- Restore the matching key from the same backup as the encrypted database and configuration.
- Do not replace the key with a newly generated one when trying to recover existing credentials.

### Installation fails

- Confirm that Python 3.10 or newer is active.
- Upgrade pip and retry installation inside the project's virtual environment.
- Review the installation output for platform-specific browser or dependency issues.

## Project status and contribution

LikePilot is under active development. See [ROADMAP.md](ROADMAP.md) for recorded implementation decisions, completed work, outstanding tasks, and verification status.

Bug reports and focused improvements are welcome through the repository's issue and pull-request workflows. Include reproducible steps, relevant sanitized logs, your operating system, Python version, and browser version when reporting a problem. Remove credentials, cookies, tokens, personal information, and other secrets before sharing diagnostic output.

## License

No license file is currently included in this repository. Unless and until a license is added, do not assume that the source code is available for unrestricted redistribution, modification, or commercial use.
