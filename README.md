# LikePilot

LikePilot is a multi-platform automation and agent-management application built with Python. It integrates multiple engagement/task providers with supported social networks through configurable automation agents. The application is managed through a local web dashboard in a browser.

LikePilot is actively developed and intended for educational, experimental, and software-development purposes. Integrations and workflows are evolving; not all functionality should be considered production-ready. Users are responsible for complying with connected services' terms and automating only accounts and environments they are authorized to use.

## Getting started

The intended workflow is:

1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install the project dependencies.
4. Configure the application using the documented setup.
5. Start the web server with the provided command.
6. Open the local dashboard URL in your browser.

The exact clean-install commands and supported Python versions will be documented after the dependency and startup audit is complete. Until then, use the existing development instructions and treat the setup workflow as evolving.

## Application model

- **Web dashboard:** the sole user interface; accessed through a standard browser.
- **Application server:** serves the dashboard and coordinates agent execution.
- **Integrations:** provider-specific and social-network-specific adapters.
- **Runtime data:** databases, profiles, logs, and backups are kept separate from application source.

## Project status

LikePilot is under active development. See [ROADMAP.md](ROADMAP.md) for verified progress, outstanding work, and migration decisions.
