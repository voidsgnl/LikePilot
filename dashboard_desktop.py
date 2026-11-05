import os
import socket
import sys
import threading
import time
from urllib.error import URLError
from urllib.request import urlopen

from core.portable import ensure_portable_runtime
from web.app import app, PROJECT_ROOT

try:
    import webview
except ImportError as error:
    raise SystemExit(
        "pywebview is required for the desktop dashboard. Install desktop dependencies first."
    ) from error

try:
    from waitress import serve as waitress_serve
except ImportError:
    waitress_serve = None


WINDOW_TITLE = "LikePilot Dashboard"
WINDOW_WIDTH = 1440
WINDOW_HEIGHT = 980
SERVER_HOST = "127.0.0.1"
SERVER_WAIT_TIMEOUT = 20.0


def _find_open_port(host=SERVER_HOST):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        sock.listen(1)
        return sock.getsockname()[1]


def _server_url(host, port):
    return f"http://{host}:{port}/login"


def _run_server(host, port):
    if waitress_serve is not None:
        waitress_serve(app, host=host, port=port, threads=8)
        return
    app.run(host=host, port=port, threaded=True, use_reloader=False)


def _wait_for_server(url, timeout=SERVER_WAIT_TIMEOUT):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=1.5) as response:
                if response.status < 500:
                    return True
        except URLError:
            pass
        except Exception:
            pass
        time.sleep(0.2)
    return False


def _ensure_runtime_folders():
    for name in ("logs", "diagnostics"):
        os.makedirs(os.path.join(PROJECT_ROOT, name), exist_ok=True)


def main():
    ensure_portable_runtime()
    _ensure_runtime_folders()
    port = _find_open_port()
    url = _server_url(SERVER_HOST, port)
    server_thread = threading.Thread(
        target=_run_server,
        args=(SERVER_HOST, port),
        daemon=True,
        name="likepilot-dashboard-server",
    )
    server_thread.start()

    if not _wait_for_server(url):
        raise SystemExit(f"Dashboard server did not start in time at {url}")

    window = webview.create_window(
        WINDOW_TITLE,
        url,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        min_size=(1120, 760),
        text_select=True,
    )
    webview.start(debug=False)
    return window


if __name__ == "__main__":
    sys.exit(main() or 0)
