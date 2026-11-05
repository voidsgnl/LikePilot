import sys

try:
    import webview
except ImportError as error:
    raise SystemExit(
        "pywebview is required for the desktop LikePilot app. Install desktop dependencies first."
    ) from error

from core.console import install_console_log_router
from core.paths import get_runtime_root
from core.portable import ensure_portable_runtime
from core.runtime import supervisor
from farm import bootstrap_agents, get_startup_urls, start_healthy_server, write_runtime_port_file


WINDOW_TITLE = "LikePilot"
WINDOW_WIDTH = 1540
WINDOW_HEIGHT = 1020


def main():
    runtime_root = get_runtime_root()
    ensure_portable_runtime()
    install_console_log_router(runtime_root)

    host = "127.0.0.1"
    preferred_port = 5001

    bootstrap_agents()
    supervisor.start()
    server, server_thread, port = start_healthy_server(host, preferred_port)

    startup_urls = get_startup_urls(host, port)
    write_runtime_port_file(port, startup_urls)
    url = startup_urls[0]

    webview.create_window(
        WINDOW_TITLE,
        url,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        min_size=(1180, 760),
        text_select=True,
    )

    try:
        webview.start(debug=False)
    finally:
        server.shutdown()
        server_thread.join(timeout=5)


if __name__ == "__main__":
    sys.exit(main() or 0)
