# Development setup

LikePilot is a web-only Python application. Development and normal use share the same server entrypoint; there is no desktop executable build or native-window dependency set.

## Environment

Use Python 3.10 or newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

The editable install configures the `src/likepilot` package and installs the runtime dependencies declared in `pyproject.toml`.

## Configuration

Copy the environment template if `.env` does not already exist:

```bash
cp .env.example .env
```

Set a unique `DASHBOARD_PASS` and a long random `FLASK_SECRET_KEY`. Preserve existing `config.json`, database, profile, and agent data when updating a checkout.

## Start and stop

```bash
python farm.py
```

Open the login URL printed by the server. Stop with Ctrl+C. The package entrypoints are also available as `python -m likepilot` and `likepilot` after installation.

## Validation

Run the structural smoke test with:

```bash
python -m pytest
```

A successful server startup is a smoke test, not proof that every provider/network workflow is operational. Verify browser setup, agent lifecycle, persistence, and each integration separately.
