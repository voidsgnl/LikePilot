import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from likepilot.core.paths import runtime_path
from likepilot.core.credentials import decrypt_secret, encrypt_secret, is_encrypted
from likepilot.core.security import redact_sensitive_text, register_secret

DB_FILE = runtime_path("likepilot.db")
LEGACY_DB_FILE = runtime_path("likeit.db")
AGENTS_FILE = runtime_path("agents.json")
LEGACY_STATS_FILE = runtime_path("stats.json")
MAX_LOGS_PER_AGENT = 200
MAX_HISTORY_POINTS = 200

_DB_LOCK = threading.RLock()


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_date_boundary(value, end_of_day=False):
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    if len(raw) == 10:
        dt = datetime.strptime(raw, "%Y-%m-%d")
        if end_of_day:
            dt = dt + timedelta(days=1)
        return dt.isoformat(timespec="seconds") + "Z"
    if raw.endswith("Z"):
        raw = raw[:-1]
    dt = datetime.fromisoformat(raw)
    if end_of_day and len(value.strip()) == 10:
        dt = dt + timedelta(days=1)
    return dt.isoformat(timespec="seconds") + "Z"


def _resolve_db_file():
    if os.path.exists(DB_FILE):
        return DB_FILE
    if os.path.exists(LEGACY_DB_FILE):
        try:
            os.replace(LEGACY_DB_FILE, DB_FILE)
            return DB_FILE
        except OSError:
            return LEGACY_DB_FILE
    return DB_FILE


@contextmanager
def _connect():
    conn = sqlite3.connect(_resolve_db_file(), timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _DB_LOCK, _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agents (
                name TEXT PRIMARY KEY,
                chrome_profile TEXT NOT NULL,
                proxy TEXT,
                login_user TEXT,
                login_password TEXT,
                enabled INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Stopped',
                credits INTEGER NOT NULL DEFAULT 0,
                site TEXT NOT NULL DEFAULT 'Like4Like',
                platform TEXT NOT NULL DEFAULT 'Twitter',
                fallback_platform TEXT,
                fallback_chain TEXT,
                comment_templates TEXT,
                switch_pending INTEGER NOT NULL DEFAULT 0,
                switch_reason TEXT,
                last_error TEXT,
                heartbeat_at TEXT,
                session_started_at TEXT,
                updated_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS credit_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                platform TEXT NOT NULL,
                credits INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        _ensure_agent_columns(conn)
        _migrate_credentials(conn)
    _import_legacy_data()


def _ensure_agent_columns(conn):
    existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(agents)").fetchall()}
    if "site" not in existing_columns:
        conn.execute("ALTER TABLE agents ADD COLUMN site TEXT NOT NULL DEFAULT 'Like4Like'")
    if "proxy" not in existing_columns:
        conn.execute("ALTER TABLE agents ADD COLUMN proxy TEXT")
    if "login_user" not in existing_columns:
        conn.execute("ALTER TABLE agents ADD COLUMN login_user TEXT")
    if "login_password" not in existing_columns:
        conn.execute("ALTER TABLE agents ADD COLUMN login_password TEXT")
    if "fallback_platform" not in existing_columns:
        conn.execute("ALTER TABLE agents ADD COLUMN fallback_platform TEXT")
    if "fallback_chain" not in existing_columns:
        conn.execute("ALTER TABLE agents ADD COLUMN fallback_chain TEXT")
    if "comment_templates" not in existing_columns:
        conn.execute("ALTER TABLE agents ADD COLUMN comment_templates TEXT")
    if "switch_pending" not in existing_columns:
        conn.execute("ALTER TABLE agents ADD COLUMN switch_pending INTEGER NOT NULL DEFAULT 0")
    if "switch_reason" not in existing_columns:
        conn.execute("ALTER TABLE agents ADD COLUMN switch_reason TEXT")
    if "last_error" not in existing_columns:
        conn.execute("ALTER TABLE agents ADD COLUMN last_error TEXT")
    if "heartbeat_at" not in existing_columns:
        conn.execute("ALTER TABLE agents ADD COLUMN heartbeat_at TEXT")
    if "session_started_at" not in existing_columns:
        conn.execute("ALTER TABLE agents ADD COLUMN session_started_at TEXT")



def _migrate_credentials(conn):
    """Encrypt legacy plaintext credentials in place without changing their values."""
    rows = conn.execute(
        "SELECT key, value FROM settings WHERE key LIKE 'provider_login.%.password' OR key LIKE 'secret.%'"
    ).fetchall()
    for row in rows:
        if row["value"] and not is_encrypted(row["value"]):
            conn.execute("UPDATE settings SET value = ? WHERE key = ?", (encrypt_secret(row["value"]), row["key"]))
    agents = conn.execute(
        "SELECT name, login_password, proxy FROM agents"
    ).fetchall()
    for agent in agents:
        if agent["login_password"] and not is_encrypted(agent["login_password"]):
            conn.execute("UPDATE agents SET login_password = ? WHERE name = ?", (encrypt_secret(agent["login_password"]), agent["name"]))
        if agent["proxy"] and not is_encrypted(agent["proxy"]):
            conn.execute("UPDATE agents SET proxy = ? WHERE name = ?", (encrypt_secret(agent["proxy"]), agent["name"]))

def _import_legacy_data():
    with _DB_LOCK, _connect() as conn:
        agent_count = conn.execute("SELECT COUNT(*) AS count FROM agents").fetchone()["count"]
        if agent_count == 0 and os.path.exists(AGENTS_FILE):
            with open(AGENTS_FILE, "r", encoding="utf-8") as f:
                legacy_agents = json.load(f)
            for agent in legacy_agents:
                now = _utc_now()
                conn.execute(
                    """
                    INSERT OR IGNORE INTO agents
                    (name, chrome_profile, proxy, enabled, status, credits, platform, updated_at, created_at)
                    VALUES (?, ?, ?, ?, 'Stopped', 0, 'Twitter', ?, ?)
                    """,
                    (
                        agent["name"],
                        agent.get("chrome_profile", "Default"),
                        agent.get("proxy"),
                        1 if agent.get("enabled") else 0,
                        now,
                        now,
                    ),
                )

        settings_count = conn.execute("SELECT COUNT(*) AS count FROM settings").fetchone()["count"]
        if settings_count == 0:
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES ('auto_switch', '0')"
            )

        history_count = conn.execute("SELECT COUNT(*) AS count FROM credit_history").fetchone()["count"]
        if history_count == 0 and os.path.exists(LEGACY_STATS_FILE):
            with open(LEGACY_STATS_FILE, "r", encoding="utf-8") as f:
                legacy_stats = json.load(f)
            for point in legacy_stats.get("history", []):
                conn.execute(
                    """
                    INSERT INTO credit_history (agent_name, platform, credits, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        None,
                        point.get("platform", "Unknown"),
                        int(point.get("credits", 0)),
                        point.get("time") or _utc_now(),
                    ),
                )


def get_auto_switch():
    init_db()
    with _DB_LOCK, _connect() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = 'auto_switch'"
        ).fetchone()
        return bool(int(row["value"])) if row else False


def set_auto_switch(enabled):
    init_db()
    with _DB_LOCK, _connect() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value) VALUES ('auto_switch', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            ("1" if enabled else "0",),
        )


def toggle_auto_switch():
    enabled = not get_auto_switch()
    set_auto_switch(enabled)
    return enabled

PROVIDER_SITES = ("Like4Like", "KingdomLikes", "YouLikeHits")


def get_provider_login_settings(site):
    if site not in PROVIDER_SITES:
        raise ValueError(f"Unsupported provider: {site}")
    init_db()
    keys = {
        "enabled": f"provider_login.{site}.enabled",
        "username": f"provider_login.{site}.username",
        "password": f"provider_login.{site}.password",
    }
    with _DB_LOCK, _connect() as conn:
        rows = conn.execute(
            "SELECT key, value FROM settings WHERE key IN (?, ?, ?)",
            tuple(keys.values()),
        ).fetchall()
    values = {row["key"]: row["value"] for row in rows}
    result = {
        "enabled": values.get(keys["enabled"], "0") == "1",
        "username": values.get(keys["username"], ""),
        "password": decrypt_secret(values.get(keys["password"], "")),
    }
    register_secret(result["password"])
    return result

def set_provider_login_settings(site, enabled, username, password=None, clear_password=False):
    if site not in PROVIDER_SITES:
        raise ValueError(f"Unsupported provider: {site}")
    init_db()
    values = {
        f"provider_login.{site}.enabled": "1" if enabled else "0",
        f"provider_login.{site}.username": (username or "").strip(),
    }
    with _DB_LOCK, _connect() as conn:
        conn.executemany(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            values.items(),
        )
        password_key = f"provider_login.{site}.password"
        if clear_password:
            conn.execute("DELETE FROM settings WHERE key = ?", (password_key,))
        elif password is not None:
            register_secret(password)
            conn.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (password_key, encrypt_secret(password)),
            )



def get_secret(name, default=""):
    """Read an encrypted application secret from the settings table."""
    if not name or not isinstance(name, str):
        raise ValueError("Secret name is required.")
    init_db()
    with _DB_LOCK, _connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (f"secret.{name}",)).fetchone()
    value = decrypt_secret(row["value"]) if row else default
    register_secret(value)
    return value


def set_secret(name, value):
    """Persist an application secret encrypted at rest; empty values clear it."""
    if not name or not isinstance(name, str):
        raise ValueError("Secret name is required.")
    init_db()
    key = f"secret.{name}"
    with _DB_LOCK, _connect() as conn:
        if value in (None, ""):
            conn.execute("DELETE FROM settings WHERE key = ?", (key,))
        else:
            register_secret(value)
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, encrypt_secret(value)),
            )

def get_agents():
    init_db()
    with _DB_LOCK, _connect() as conn:
        rows = conn.execute(
            """
            SELECT name, chrome_profile, proxy, enabled
            FROM agents
            ORDER BY created_at, name
            """
        ).fetchall()
        agents = [dict(row) for row in rows]
        for agent in agents:
            agent["proxy"] = decrypt_secret(agent["proxy"]) if agent["proxy"] else None
            register_secret(agent["proxy"])
        return agents


def add_agent(
    name,
    profile,
    proxy=None,
    enabled=False,
    site="Like4Like",
    fallback_platform=None,
    fallback_chain=None,
    comment_templates=None,
    login_user=None,
    login_password=None,
):
    init_db()
    now = _utc_now()
    with _DB_LOCK, _connect() as conn:
        conn.execute(
            """
            INSERT INTO agents
            (name, chrome_profile, proxy, login_user, login_password, enabled, status, credits, site, platform, fallback_platform, fallback_chain, comment_templates, switch_pending, switch_reason, session_started_at, updated_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'Stopped', 0, ?, 'Twitter', ?, ?, ?, 0, NULL, NULL, ?, ?)
            """,
            (
                name,
                profile,
                proxy,
                login_user,
                encrypt_secret(login_password),
                1 if enabled else 0,
                site,
                fallback_platform,
                fallback_chain,
                comment_templates,
                now,
                now,
            ),
        )
    append_agent_log(name, "AGENT_CREATED", level="SYSTEM")


def remove_agent(name):
    init_db()
    with _DB_LOCK, _connect() as conn:
        conn.execute("DELETE FROM agent_logs WHERE agent_name = ?", (name,))
        conn.execute("DELETE FROM credit_history WHERE agent_name = ?", (name,))
        conn.execute("DELETE FROM agents WHERE name = ?", (name,))


def get_agent(name):
    init_db()
    with _DB_LOCK, _connect() as conn:
        row = conn.execute("SELECT * FROM agents WHERE name = ?", (name,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result.pop("login_password", None)
        result["proxy"] = decrypt_secret(result["proxy"]) if result.get("proxy") else None
        register_secret(result.get("proxy"))
        return result


def rename_agent(current_name, new_name):
    init_db()
    if current_name == new_name:
        return
    with _DB_LOCK, _connect() as conn:
        conn.execute("UPDATE agents SET name = ?, updated_at = ? WHERE name = ?", (new_name, _utc_now(), current_name))
        conn.execute("UPDATE agent_logs SET agent_name = ? WHERE agent_name = ?", (new_name, current_name))
        conn.execute("UPDATE credit_history SET agent_name = ? WHERE agent_name = ?", (new_name, current_name))


def update_agent(name, **fields):
    init_db()
    if not fields:
        return
    allowed = {
        "chrome_profile",
        "proxy",
        "login_user",
        "login_password",
        "enabled",
        "status",
        "credits",
        "site",
        "platform",
        "fallback_platform",
        "fallback_chain",
        "comment_templates",
        "switch_pending",
        "switch_reason",
        "last_error",
        "heartbeat_at",
        "session_started_at",
    }
    assignments = []
    values = []
    for key, value in fields.items():
        if key not in allowed:
            continue
        if key == "proxy":
            register_secret(value)
        assignments.append(f"{key} = ?")
        if key in {"login_password", "proxy"}:
            value = encrypt_secret(value)
        elif key == "last_error":
            value = redact_sensitive_text(value)
        values.append(value)
    if not assignments:
        return
    assignments.append("updated_at = ?")
    values.append(_utc_now())
    values.append(name)
    with _DB_LOCK, _connect() as conn:
        conn.execute(
            f"UPDATE agents SET {', '.join(assignments)} WHERE name = ?",
            values,
        )


def heartbeat_agent(name, status=None):
    updates = {"heartbeat_at": _utc_now()}
    if status:
        updates["status"] = status
    update_agent(name, **updates)


def append_agent_log(name, message, level="INFO"):
    message = redact_sensitive_text(message)
    init_db()
    with _DB_LOCK, _connect() as conn:
        conn.execute(
            """
            INSERT INTO agent_logs (agent_name, level, message, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (name, level, message, _utc_now()),
        )
        conn.execute(
            """
            DELETE FROM agent_logs
            WHERE agent_name = ?
              AND id NOT IN (
                  SELECT id FROM agent_logs
                  WHERE agent_name = ?
                  ORDER BY id DESC
                  LIMIT ?
              )
            """,
            (name, name, MAX_LOGS_PER_AGENT),
        )


def list_agent_logs(name, limit=5):
    init_db()
    with _DB_LOCK, _connect() as conn:
        rows = conn.execute(
            """
            SELECT level, message, created_at
            FROM agent_logs
            WHERE agent_name = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (name, limit),
        ).fetchall()
    formatted = []
    for row in reversed(rows):
        formatted.append(redact_sensitive_text(f"{row['created_at']} [{row['level']}] {row['message']}"))
    return formatted


def list_runtime_status():
    init_db()
    with _DB_LOCK, _connect() as conn:
        rows = conn.execute(
            """
            SELECT name, chrome_profile, proxy, status, credits, site, platform, fallback_platform, fallback_chain, switch_pending, switch_reason, last_error, heartbeat_at, session_started_at
                 , comment_templates
            FROM agents
            ORDER BY created_at, name
            """
        ).fetchall()
        session_rows = conn.execute(
            """
            SELECT
                a.name AS agent_name,
                MIN(ch.credits) AS min_credits,
                MAX(ch.credits) AS max_credits,
                COUNT(ch.id) AS samples
            FROM agents a
            LEFT JOIN credit_history ch
                ON ch.agent_name = a.name
               AND a.session_started_at IS NOT NULL
               AND ch.created_at >= a.session_started_at
            GROUP BY a.name
            """
        ).fetchall()
    session_map = {row["agent_name"]: dict(row) for row in session_rows}
    agents = {}
    for row in rows:
        name = row["name"]
        proxy_value = decrypt_secret(row["proxy"]) if row["proxy"] else None
        register_secret(proxy_value)
        session = session_map.get(name, {})
        min_credits = session.get("min_credits")
        max_credits = session.get("max_credits")
        session_gain = 0
        if min_credits is not None and max_credits is not None:
            session_gain = max_credits - min_credits
        agents[name] = {
            "status": row["status"],
            "credits": row["credits"],
            "session_gain": session_gain,
            "session_peak": max_credits if max_credits is not None else row["credits"],
            "samples": session.get("samples", 0),
            "logs": list_agent_logs(name, limit=5),
            "site": row["site"],
            "platform": row["platform"],
            "chrome_profile": row["chrome_profile"],
            "proxy": proxy_value or "",
            "fallback_platform": row["fallback_platform"],
            "fallback_chain": row["fallback_chain"] or "",
            "comment_templates": row["comment_templates"] or "",
            "switch_pending": bool(row["switch_pending"]),
            "switch_reason": row["switch_reason"],
            "last_error": redact_sensitive_text(row["last_error"] or ""),
            "heartbeat_at": row["heartbeat_at"],
            "session_started_at": row["session_started_at"],
        }
    return {"agents": agents, "auto_switch": get_auto_switch()}


def log_credit_update(platform, credits, agent_name=None):
    init_db()
    with _DB_LOCK, _connect() as conn:
        conn.execute(
            """
            INSERT INTO credit_history (agent_name, platform, credits, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (agent_name, platform, int(credits), _utc_now()),
        )
        conn.execute(
            """
            DELETE FROM credit_history
            WHERE id NOT IN (
                SELECT id FROM credit_history
                ORDER BY id DESC
                LIMIT ?
            )
            """,
            (MAX_HISTORY_POINTS,),
        )


def get_stats():
    init_db()
    with _DB_LOCK, _connect() as conn:
        history_rows = conn.execute(
            """
            SELECT platform, credits, created_at
            FROM credit_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (50,),
        ).fetchall()
        platform_rows = conn.execute(
            """
            SELECT platform, COUNT(*) AS count
            FROM credit_history
            GROUP BY platform
            ORDER BY count DESC, platform ASC
            """
        ).fetchall()
        summary = conn.execute(
            """
            SELECT
                COUNT(*) AS samples,
                COALESCE(MIN(credits), 0) AS min_credits,
                COALESCE(MAX(credits), 0) AS max_credits,
                COALESCE((SELECT credits FROM credit_history ORDER BY id DESC LIMIT 1), 0) AS latest_credits
            FROM credit_history
            """
        ).fetchone()
    history = []
    for row in reversed(history_rows):
        timestamp = row["created_at"]
        history.append(
            {
                "time": timestamp[11:19] if "T" in timestamp else timestamp,
                "credits": row["credits"],
                "platform": row["platform"],
            }
        )
    platform_stats = {row["platform"]: row["count"] for row in platform_rows}
    metrics = {
        "latest_credits": summary["latest_credits"],
        "session_peak": summary["max_credits"],
        "session_floor": summary["min_credits"],
        "session_gain": summary["max_credits"] - summary["min_credits"] if summary["samples"] else 0,
        "samples": summary["samples"],
    }
    return {"history": history, "platform_stats": platform_stats, "metrics": metrics}


def export_activity(start_date=None, end_date=None):
    init_db()
    start_at = _parse_date_boundary(start_date)
    end_before = _parse_date_boundary(end_date, end_of_day=True)

    history_filters = []
    history_params = []
    log_filters = []
    log_params = []

    if start_at:
        history_filters.append("created_at >= ?")
        history_params.append(start_at)
        log_filters.append("created_at >= ?")
        log_params.append(start_at)
    if end_before:
        history_filters.append("created_at < ?")
        history_params.append(end_before)
        log_filters.append("created_at < ?")
        log_params.append(end_before)

    history_where = f"WHERE {' AND '.join(history_filters)}" if history_filters else ""
    log_where = f"WHERE {' AND '.join(log_filters)}" if log_filters else ""

    with _DB_LOCK, _connect() as conn:
        credit_rows = conn.execute(
            f"""
            SELECT created_at, 'credit' AS activity_type, COALESCE(agent_name, '') AS agent_name, platform, credits, '' AS level, '' AS message
            FROM credit_history
            {history_where}
            ORDER BY created_at ASC, id ASC
            """,
            history_params,
        ).fetchall()
        log_rows = conn.execute(
            f"""
            SELECT created_at, 'log' AS activity_type, agent_name, '' AS platform, NULL AS credits, level, message
            FROM agent_logs
            {log_where}
            ORDER BY created_at ASC, id ASC
            """,
            log_params,
        ).fetchall()
        platform_rows = conn.execute(
            f"""
            SELECT platform, COUNT(*) AS count
            FROM credit_history
            {history_where}
            GROUP BY platform
            ORDER BY count DESC, platform ASC
            """,
            history_params,
        ).fetchall()
        summary = conn.execute(
            f"""
            SELECT
                COUNT(*) AS samples,
                COALESCE(MIN(credits), 0) AS min_credits,
                COALESCE(MAX(credits), 0) AS max_credits,
                COALESCE((
                    SELECT credits
                    FROM credit_history
                    {history_where}
                    ORDER BY id DESC
                    LIMIT 1
                ), 0) AS latest_credits
            FROM credit_history
            {history_where}
            """,
            history_params + history_params,
        ).fetchone()

    activities = sorted(
        [dict(row) for row in credit_rows] + [dict(row) for row in log_rows],
        key=lambda row: (row["created_at"], row["activity_type"], row.get("agent_name") or ""),
    )
    platform_stats = {row["platform"]: row["count"] for row in platform_rows}
    metrics = {
        "latest_credits": summary["latest_credits"],
        "session_peak": summary["max_credits"],
        "session_floor": summary["min_credits"],
        "session_gain": summary["max_credits"] - summary["min_credits"] if summary["samples"] else 0,
        "samples": summary["samples"],
        "activity_count": len(activities),
    }
    return {
        "range": {
            "start_date": start_date or "",
            "end_date": end_date or "",
            "start_at": start_at or "",
            "end_before": end_before or "",
        },
        "metrics": metrics,
        "platform_stats": platform_stats,
        "activities": activities,
    }
