from likepilot.core.runtime import supervisor
from likepilot.core.console import install_console_log_router
from likepilot.core.paths import get_runtime_root, runtime_path
from likepilot.core.state import append_agent_log, get_agents, init_db, update_agent
from likepilot.dashboard.app import app
import os
import socket
import threading
import time
import urllib.request
from dotenv import load_dotenv
from werkzeug.serving import make_server

RUNTIME_ROOT = get_runtime_root()

load_dotenv(dotenv_path=runtime_path(".env"), override=False)


def bootstrap_agents():
    init_db()
    for agent in get_agents():
        update_agent(agent["name"], status="Stopped")
        append_agent_log(agent["name"], "AGENT_BOOT_SEQUENCE_COMPLETE", level="SYSTEM")


def get_startup_urls(host, port):
    urls = [f"http://127.0.0.1:{port}/login", f"http://localhost:{port}/login"]
    if host not in {"127.0.0.1", "localhost"}:
        try:
            lan_ip = socket.gethostbyname(socket.gethostname())
            if lan_ip and not lan_ip.startswith("127."):
                urls.append(f"http://{lan_ip}:{port}/login")
        except OSError:
            pass
    return urls


def is_port_available(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def pick_startup_port(host, preferred_port, span=20):
    candidates = []
    if preferred_port not in candidates:
        candidates.append(preferred_port)
    for port in range(preferred_port + 1, preferred_port + span + 1):
        candidates.append(port)

    hosts_to_try = [host]
    if host == "0.0.0.0":
        hosts_to_try.append("127.0.0.1")

    for port in candidates:
        if all(is_port_available(candidate_host, port) for candidate_host in hosts_to_try):
            return port
    raise RuntimeError(f"No available dashboard port found in range {preferred_port}-{preferred_port + span}.")


def can_serve_http(host, port, timeout_seconds=3):
    probe_host = "127.0.0.1" if host in {"0.0.0.0", "127.0.0.1", "localhost"} else host
    url = f"http://{probe_host}:{port}/login"
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.5) as response:
                return 200 <= response.status < 500
        except Exception:
            time.sleep(0.2)
    return False


def start_healthy_server(host, preferred_port, span=20):
    attempted = []
    for port in [preferred_port] + list(range(preferred_port + 1, preferred_port + span + 1)):
        if not is_port_available(host, port):
            continue
        try:
            server = make_server(host, port, app, threaded=True)
        except OSError:
            continue

        thread = threading.Thread(target=server.serve_forever, daemon=False)
        thread.start()

        if can_serve_http(host, port):
            return server, thread, port

        attempted.append(port)
        server.shutdown()
        thread.join(timeout=2)

    attempted_text = ", ".join(str(port) for port in attempted) or f"{preferred_port}-{preferred_port + span}"
    raise RuntimeError(f"Could not start a healthy HTTP server on ports {attempted_text}.")


def write_runtime_port_file(port, urls):
    path = runtime_path("runtime_port.txt")
    lines = [
        f"PORT={port}",
        *[f"URL={url}" for url in urls],
    ]
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return path


def main():
    install_console_log_router(RUNTIME_ROOT)
    host = os.getenv("DASHBOARD_HOST", "127.0.0.1")
    preferred_port = int(os.getenv("DASHBOARD_PORT", "5001"))
    bootstrap_agents()
    supervisor.start()
    server, server_thread, port = start_healthy_server(host, preferred_port)
    print("LIKEPILOT MISSION CONTROL ACTIVE")
    if port != preferred_port:
        print(f"Configured port {preferred_port} is unavailable or unhealthy. Using {port} instead.")
    startup_urls = get_startup_urls(host, port)
    port_file = write_runtime_port_file(port, startup_urls)
    print(f"Runtime port file: {port_file}")
    for url in startup_urls:
        print(f"Open {url}")
    try:
        server_thread.join()
    except KeyboardInterrupt:
        server.shutdown()
        server_thread.join(timeout=5)


if __name__ == "__main__":
    main()
