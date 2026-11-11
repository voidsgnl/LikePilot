# Contributing

Thank you for considering a contribution to LikePilot.

## Before opening an issue

- Search existing issues for the same problem.
- Use a current checkout of `main`.
- Include reproducible steps, expected behaviour, and actual behaviour.
- Include your operating system, Python version, and browser version where relevant.
- Sanitize logs and screenshots. Never attach credentials, cookies, access tokens, browser profiles, databases, or personal information.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

On Windows, activate the environment with `.venv\\Scripts\\Activate.ps1`.

## Checks

Before submitting a pull request, run:

```bash
python -m compileall -q src tests
python -m pytest -q
ruff check .
```

Add or update tests for behavioural changes. Update documentation when configuration, setup, security expectations, or user-facing behaviour changes.

## Pull requests

- Keep each change focused and explain the reason for it.
- Describe relevant compatibility or migration effects.
- Do not commit runtime data, local environment files, generated browser profiles, logs, databases, or secrets.
- Do not claim a provider integration is verified unless it has been tested against the live provider.
- Avoid unrelated formatting changes.

## Security issues

Do not open a public issue for a vulnerability. Follow [SECURITY.md](SECURITY.md).
