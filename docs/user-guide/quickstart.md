# LikePilot quick start

1. Clone the repository and enter the project directory.
2. Create and activate a Python virtual environment.
3. Install with `python -m pip install -e .`.
4. Copy `.env.example` to `.env` if needed and set your dashboard password and secret key.
5. Run `python farm.py`.
6. Open the login URL printed by the server in your browser.
7. Stop the server with Ctrl+C.

LikePilot runs as a web application. It does not require a desktop executable, pywebview, or WebView2.

Keep your existing database, configuration, profiles, and logs when upgrading. Runtime-data relocation is a separate migration and must not be performed by manually deleting existing files.
