from flask import Flask, Response, render_template, jsonify, request, session, redirect, url_for, stream_with_context, send_from_directory
import os
import json
import time
import csv
import io
import sqlite3
from functools import wraps
from contextlib import contextmanager
from dotenv import load_dotenv
from likepilot.core.paths import get_runtime_root, runtime_path
from likepilot.core.agents import add_agent, remove_agent
from likepilot.core.runtime import supervisor
from likepilot.core.state import (
    _resolve_db_file,
    append_agent_log,
    export_activity,
    get_agent,
    get_stats,
    init_db,
    list_runtime_status,
    rename_agent,
    toggle_auto_switch as toggle_auto_switch_setting,
    update_agent,
)

RUNTIME_ROOT = get_runtime_root()

load_dotenv(dotenv_path=runtime_path(".env"), override=True)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or os.urandom(24)
PROJECT_ROOT = RUNTIME_ROOT
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
DIAGNOSTICS_DIR = os.path.join(PROJECT_ROOT, "diagnostics")
BRAND_DIR = os.path.join(os.path.dirname(__file__), "favicon")
DATABASE_PREVIEW_LIMIT = 100
LOG_TAIL_LIMIT = 400

# Dashboard Credentials
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASS = os.getenv("DASHBOARD_PASS", "likepilot2026")

init_db()


def _utc_timestamp(value):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(value))


def _quote_identifier(name):
    return '"' + str(name).replace('"', '""') + '"'


@contextmanager
def _database_connection():
    conn = sqlite3.connect(_resolve_db_file(), timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _list_database_tables():
    init_db()
    with _database_connection() as conn:
        rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name ASC
            """
        ).fetchall()
        tables = []
        for row in rows:
            table_name = row["name"]
            quoted_table = _quote_identifier(table_name)
            columns = [
                {
                    "name": column["name"],
                    "type": column["type"] or "",
                    "notnull": bool(column["notnull"]),
                    "primary_key": bool(column["pk"]),
                }
                for column in conn.execute(f"PRAGMA table_info({quoted_table})").fetchall()
            ]
            foreign_keys = [
                {
                    "from_column": foreign_key["from"],
                    "to_table": foreign_key["table"],
                    "to_column": foreign_key["to"],
                }
                for foreign_key in conn.execute(f"PRAGMA foreign_key_list({quoted_table})").fetchall()
            ]
            count_row = conn.execute(f"SELECT COUNT(*) AS count FROM {quoted_table}").fetchone()
            tables.append(
                {
                    "name": table_name,
                    "row_count": int(count_row["count"]) if count_row else 0,
                    "columns": columns,
                    "foreign_keys": foreign_keys,
                }
            )
        return tables


def _read_database_table(table_name, limit=DATABASE_PREVIEW_LIMIT):
    limit = max(1, min(int(limit or DATABASE_PREVIEW_LIMIT), DATABASE_PREVIEW_LIMIT))
    tables = _list_database_tables()
    table_map = {table["name"]: table for table in tables}
    if table_name not in table_map:
        return None

    quoted_table = _quote_identifier(table_name)
    with _database_connection() as conn:
        columns = table_map[table_name]["columns"]
        column_names = [column["name"] for column in columns]
        order_column = "id" if "id" in column_names else ("created_at" if "created_at" in column_names else None)
        order_clause = f" ORDER BY {_quote_identifier(order_column)} DESC" if order_column else ""
        rows = conn.execute(
            f"SELECT * FROM {quoted_table}{order_clause} LIMIT ?",
            (limit,),
        ).fetchall()
    return {
        "table": table_name,
        "row_count": table_map[table_name]["row_count"],
        "columns": columns,
        "rows": [dict(row) for row in rows],
        "limit": limit,
    }


def _safe_file_path(base_dir, name):
    filename = os.path.basename((name or "").strip())
    if not filename or filename in {".", ".."}:
        return None, None
    path = os.path.join(base_dir, filename)
    if not os.path.isfile(path):
        return filename, None
    return filename, path


def _list_directory_files(base_dir, allowed_extensions=None):
    if not os.path.isdir(base_dir):
        return []
    entries = []
    for entry in os.scandir(base_dir):
        if not entry.is_file():
            continue
        if allowed_extensions and os.path.splitext(entry.name)[1].lower() not in allowed_extensions:
            continue
        stats = entry.stat()
        entries.append(
            {
                "name": entry.name,
                "size_bytes": int(stats.st_size),
                "modified_at": _utc_timestamp(stats.st_mtime),
                "modified_epoch": float(stats.st_mtime),
            }
        )
    entries.sort(key=lambda item: (item["modified_epoch"], item["name"].lower()), reverse=True)
    return entries


def _list_logs():
    return [
        {
            "name": item["name"],
            "size_bytes": item["size_bytes"],
            "modified_at": item["modified_at"],
            "is_latest": item["name"].lower() == "latest.log",
        }
        for item in _list_directory_files(LOGS_DIR, allowed_extensions={".log"})
    ]


def _read_log_file(name, tail=LOG_TAIL_LIMIT):
    filename, path = _safe_file_path(LOGS_DIR, name)
    if not path:
        return None
    tail = max(20, min(int(tail or LOG_TAIL_LIMIT), 2000))
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        lines = handle.readlines()
    content = "".join(lines[-tail:])
    return {
        "name": filename,
        "tail": tail,
        "line_count": len(lines),
        "content": content,
    }


def _list_diagnostic_groups():
    groups = {}
    for item in _list_directory_files(DIAGNOSTICS_DIR, allowed_extensions={".html", ".png"}):
        stem, ext = os.path.splitext(item["name"])
        group = groups.setdefault(
            stem,
            {
                "id": stem,
                "label": stem.replace("_", " "),
                "modified_at": item["modified_at"],
                "modified_epoch": item["modified_epoch"],
                "html_file": None,
                "image_file": None,
                "files": [],
            },
        )
        if item["modified_epoch"] > group["modified_epoch"]:
            group["modified_epoch"] = item["modified_epoch"]
            group["modified_at"] = item["modified_at"]
        if ext.lower() == ".html":
            group["html_file"] = item["name"]
        elif ext.lower() == ".png":
            group["image_file"] = item["name"]
        group["files"].append(
            {
                "name": item["name"],
                "size_bytes": item["size_bytes"],
                "modified_at": item["modified_at"],
            }
        )
    ordered = list(groups.values())
    ordered.sort(key=lambda item: (item["modified_epoch"], item["id"].lower()), reverse=True)
    for item in ordered:
        item.pop("modified_epoch", None)
    return ordered


def _delete_diagnostic_group(group_id):
    group_id = os.path.basename((group_id or "").strip())
    if not group_id:
        return 0
    deleted = 0
    if not os.path.isdir(DIAGNOSTICS_DIR):
        return deleted
    for entry in os.scandir(DIAGNOSTICS_DIR):
        if not entry.is_file():
            continue
        stem, ext = os.path.splitext(entry.name)
        if stem != group_id or ext.lower() not in {".html", ".png"}:
            continue
        os.remove(entry.path)
        deleted += 1
    return deleted

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            if request.is_json: return jsonify({"message": "Unauthorized"}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form.get('username') == DASHBOARD_USER and request.form.get('password') == DASHBOARD_PASS:
            session['logged_in'] = True
            return redirect(url_for('index'))
        error = "ACCESS_DENIED"
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


@app.route('/favicon/<path:filename>')
def brand_asset(filename):
    safe_name = os.path.basename(filename)
    if not safe_name:
        return jsonify({"message": "File not found"}), 404
    return send_from_directory(BRAND_DIR, safe_name, as_attachment=False)

@app.route('/')
@login_required
def index():
    return render_template('index.html', page="grid")


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', page="dashboard")

@app.route('/analytics')
@login_required
def analytics():
    return render_template('analytics.html', page="analytics")

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html', page="settings")


@app.route('/operations')
@login_required
def operations():
    return render_template('operations.html', page="operations")

@app.route('/api/status')
@login_required
def get_status():
    return jsonify(list_runtime_status())

@app.route('/api/stream/status')
@login_required
def stream_status():
    @stream_with_context
    def generate():
        while True:
            payload = json.dumps(list_runtime_status())
            yield f"data: {payload}\n\n"
            time.sleep(2)
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/agents/add', methods=['POST'])
@login_required
def api_add_agent():
    data = request.json
    name = (data.get("name") or "").strip()
    profile = (data.get("profile") or "").strip()
    site = (data.get("site") or "Like4Like").strip()
    fallback_platform = (data.get("fallback_platform") or "").strip() or None
    fallback_chain = (data.get("fallback_chain") or "").strip() or None
    comment_templates = (data.get("comment_templates") or "").strip() or None
    proxy = (data.get("proxy") or "").strip() or None
    login_user = (data.get("login_user") or "").strip() or None
    login_password = (data.get("login_password") or "").strip() or None
    if name and profile:
        add_agent(
            name,
            profile,
            proxy=proxy,
            site=site,
            fallback_platform=fallback_platform,
            fallback_chain=fallback_chain,
            comment_templates=comment_templates,
            login_user=login_user,
            login_password=login_password,
        )
        return jsonify({"message": f"Agent {name} added."})
    return jsonify({"message": "Invalid data"}), 400

@app.route('/api/agents/remove', methods=['POST'])
@login_required
def api_remove_agent():
    name = request.json.get("name")
    if get_agent(name):
        remove_agent(name)
        return jsonify({"message": f"Agent {name} terminated."})
    return jsonify({"message": "Agent not found"}), 404


@app.route('/api/agents/update', methods=['POST'])
@login_required
def api_update_agent():
    data = request.json or {}
    current_name = (data.get("current_name") or "").strip()
    new_name = (data.get("name") or "").strip()
    profile = (data.get("profile") or "").strip()
    site = (data.get("site") or "Like4Like").strip()
    fallback_platform = (data.get("fallback_platform") or "").strip() or None
    fallback_chain = (data.get("fallback_chain") or "").strip() or None
    comment_templates = (data.get("comment_templates") or "").strip() or None
    proxy = (data.get("proxy") or "").strip() or None
    login_user = (data.get("login_user") or "").strip() or None
    login_password = data.get("login_password")
    login_password = login_password.strip() if isinstance(login_password, str) else None

    current = get_agent(current_name)
    if not current:
        return jsonify({"message": "Agent not found"}), 404

    if current["status"] != "Stopped":
        return jsonify({"message": "Stop the agent before editing its name or profile."}), 409

    if not new_name or not profile:
        return jsonify({"message": "Agent name and profile are required."}), 400

    if new_name != current_name and get_agent(new_name):
        return jsonify({"message": "Another agent already uses that name."}), 409

    final_name = current_name
    if new_name != current_name:
        rename_agent(current_name, new_name)
        final_name = new_name

    if site != current["site"]:
        update_agent(final_name, site=site)
    if profile != current["chrome_profile"]:
        update_agent(final_name, chrome_profile=profile)
    if proxy != current.get("proxy"):
        update_agent(final_name, proxy=proxy)
    if login_user != current.get("login_user"):
        update_agent(final_name, login_user=login_user)
    if login_password is not None and login_password != (current.get("login_password") or ""):
        update_agent(final_name, login_password=login_password or None)
    if fallback_platform != current.get("fallback_platform"):
        update_agent(final_name, fallback_platform=fallback_platform)
    if fallback_chain != current.get("fallback_chain"):
        update_agent(final_name, fallback_chain=fallback_chain)
    if comment_templates != current.get("comment_templates"):
        update_agent(final_name, comment_templates=comment_templates)

    append_agent_log(
        final_name,
        f"Agent settings updated. Name: {final_name}. Site: {site}. Profile: {profile}. Proxy: {proxy or 'None'}. Login user: {login_user or 'Env default'}. Fallback: {fallback_platform or 'None'}. Chain: {fallback_chain or 'None'}. IG comments: {'Custom list set' if comment_templates else 'Default set'}.",
        level="SYSTEM",
    )
    return jsonify({"message": f"Agent {final_name} updated."})

@app.route('/api/control', methods=['POST'])
@login_required
def control_agent():
    data = request.json
    name = data.get("name")
    action = data.get("action")
    
    current = get_agent(name)
    if not current:
        return jsonify({"message": "Invalid Agent"}), 404
    
    if action == 'start':
        update_agent(
            name,
            status="Awaiting Login",
            last_error=None,
            switch_pending=0,
            switch_reason=None,
            session_started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        append_agent_log(name, "Start requested by operator.", level="SYSTEM")
    elif action == 'initialize':
        if current["status"] == "Login Success":
            update_agent(name, status="Running")
            append_agent_log(name, "Initialize received. Automation may proceed.", level="SYSTEM")
    elif action == 'ready':
        if current["status"] in {"Awaiting Login", "Login Success"}:
            update_agent(name, status="Running")
            append_agent_log(name, "Ready received. Automation may proceed.", level="SYSTEM")
    elif action == 'pause':
        if current["status"] == "Running":
            update_agent(name, status="Paused")
            pause_sent = supervisor.pause_agent(name)
            append_agent_log(name, "Pause requested by operator.", level="SYSTEM")
            if not pause_sent:
                append_agent_log(name, "Pause request reached the API, but the active bot was not available for interruption.", level="WARNING")
    elif action == 'resume':
        if current["status"] == "Paused":
            update_agent(name, status="Running")
            append_agent_log(name, "Resume requested by operator.", level="SYSTEM")
    elif action == 'stop':
        update_agent(name, status="Stopped", session_started_at=None)
        append_agent_log(name, "Stop requested by operator.", level="SYSTEM")
        
    return jsonify({"message": f"Agent {name} command: {action}"})

@app.route('/api/platform', methods=['POST'])
@login_required
def update_platform():
    data = request.json
    name = data.get("name")
    current = get_agent(name)
    if not current:
        return jsonify({"message": "Invalid Agent"}), 404
    updates = {
        "platform": data.get("platform", "Twitter"),
        "switch_pending": 0,
        "switch_reason": None,
    }
    if current["status"] == "Awaiting Switch":
        updates["status"] = "Running"
    update_agent(name, **updates)
    append_agent_log(name, f"Platform set to {data.get('platform', 'Twitter')}.", level="SYSTEM")
    return jsonify({"message": "Platform updated"})

@app.route('/api/toggle_auto_switch', methods=['POST'])
@login_required
def toggle_auto_switch():
    enabled = toggle_auto_switch_setting()
    return jsonify({"message": "Auto-switch toggled", "enabled": enabled})

@app.route('/api/stats')
@login_required
def get_stats_api():
    return jsonify(get_stats())

@app.route('/api/stream/stats')
@login_required
def stream_stats():
    @stream_with_context
    def generate():
        while True:
            payload = json.dumps(get_stats())
            yield f"data: {payload}\n\n"
            time.sleep(5)
    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/export')
@login_required
def export_activity_api():
    start_date = (request.args.get("start_date") or "").strip() or None
    end_date = (request.args.get("end_date") or "").strip() or None
    export_format = ((request.args.get("format") or "csv").strip() or "csv").lower()
    payload = export_activity(start_date=start_date, end_date=end_date)

    if export_format == "json":
        filename = f"likepilot-activity-{start_date or 'all'}-{end_date or 'all'}.json"
        return Response(
            json.dumps(payload, indent=2),
            mimetype="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["metric", "value"])
    for key, value in payload["metrics"].items():
        writer.writerow([key, value])
    writer.writerow([])
    writer.writerow(["platform", "sample_count"])
    for platform, count in payload["platform_stats"].items():
        writer.writerow([platform, count])
    writer.writerow([])
    writer.writerow(["created_at", "activity_type", "agent_name", "platform", "credits", "level", "message"])
    for item in payload["activities"]:
        writer.writerow([
            item.get("created_at", ""),
            item.get("activity_type", ""),
            item.get("agent_name", ""),
            item.get("platform", ""),
            item.get("credits", ""),
            item.get("level", ""),
            item.get("message", ""),
        ])

    filename = f"likepilot-activity-{start_date or 'all'}-{end_date or 'all'}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.route('/api/operations/database')
@login_required
def operations_database():
    db_path = os.path.join(PROJECT_ROOT, _resolve_db_file())
    tables = _list_database_tables()
    size_bytes = os.path.getsize(db_path) if os.path.exists(db_path) else 0
    relationships = []
    for table in tables:
        for foreign_key in table.get("foreign_keys", []):
            relationships.append(
                {
                    "from_table": table["name"],
                    "from_column": foreign_key["from_column"],
                    "to_table": foreign_key["to_table"],
                    "to_column": foreign_key["to_column"],
                }
            )
    return jsonify(
        {
            "database": {
                "path": db_path,
                "size_bytes": size_bytes,
                "table_count": len(tables),
                "relationship_count": len(relationships),
            },
            "tables": tables,
            "relationships": relationships,
        }
    )


@app.route('/api/operations/database/table')
@login_required
def operations_database_table():
    table_name = (request.args.get("name") or "").strip()
    limit = request.args.get("limit", DATABASE_PREVIEW_LIMIT)
    payload = _read_database_table(table_name, limit=limit)
    if not payload:
        return jsonify({"message": "Table not found"}), 404
    return jsonify(payload)


@app.route('/api/operations/logs')
@login_required
def operations_logs():
    return jsonify({"logs": _list_logs()})


@app.route('/api/operations/logs/read')
@login_required
def operations_logs_read():
    name = (request.args.get("name") or "").strip()
    tail = request.args.get("tail", LOG_TAIL_LIMIT)
    payload = _read_log_file(name, tail=tail)
    if not payload:
        return jsonify({"message": "Log file not found"}), 404
    return jsonify(payload)


@app.route('/api/operations/logs/clear', methods=['POST'])
@login_required
def operations_logs_clear():
    data = request.json or {}
    filename, path = _safe_file_path(LOGS_DIR, data.get("name"))
    if not path:
        return jsonify({"message": "Log file not found"}), 404
    with open(path, "w", encoding="utf-8"):
        pass
    return jsonify({"message": f"Cleared {filename}."})


@app.route('/api/operations/logs/delete', methods=['POST'])
@login_required
def operations_logs_delete():
    data = request.json or {}
    filename, path = _safe_file_path(LOGS_DIR, data.get("name"))
    if not path:
        return jsonify({"message": "Log file not found"}), 404
    try:
        os.remove(path)
    except OSError as error:
        return jsonify({"message": f"Unable to delete {filename}: {error}"}), 409
    return jsonify({"message": f"Deleted {filename}."})


@app.route('/api/operations/diagnostics')
@login_required
def operations_diagnostics():
    return jsonify({"captures": _list_diagnostic_groups()})


@app.route('/api/operations/diagnostics/file/<path:filename>')
@login_required
def operations_diagnostics_file(filename):
    safe_name = os.path.basename(filename)
    if not safe_name:
        return jsonify({"message": "File not found"}), 404
    return send_from_directory(DIAGNOSTICS_DIR, safe_name, as_attachment=False)


@app.route('/api/operations/diagnostics/delete', methods=['POST'])
@login_required
def operations_diagnostics_delete():
    data = request.json or {}
    group_id = data.get("group")
    try:
        deleted = _delete_diagnostic_group(group_id)
    except OSError as error:
        return jsonify({"message": f"Unable to delete diagnostic capture: {error}"}), 409
    if not deleted:
        return jsonify({"message": "Diagnostic capture not found"}), 404
    return jsonify({"message": f"Deleted {deleted} diagnostic file(s)."})


@app.route('/api/operations/diagnostics/clear', methods=['POST'])
@login_required
def operations_diagnostics_clear():
    deleted = 0
    try:
        if os.path.isdir(DIAGNOSTICS_DIR):
            for entry in os.scandir(DIAGNOSTICS_DIR):
                if not entry.is_file():
                    continue
                if os.path.splitext(entry.name)[1].lower() not in {".html", ".png"}:
                    continue
                os.remove(entry.path)
                deleted += 1
    except OSError as error:
        return jsonify({"message": f"Unable to clear diagnostics: {error}"}), 409
    return jsonify({"message": f"Deleted {deleted} diagnostic file(s)."})

def run_dashboard():
    host = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    port = int(os.getenv("DASHBOARD_PORT", "5001"))
    app.run(host=host, port=port, threaded=True)

if __name__ == '__main__':
    run_dashboard()
