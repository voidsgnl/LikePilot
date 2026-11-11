# Persistence model and migration strategy

This document describes the supported runtime data layout and the canonical SQLite schema. Source code is under src/likepilot; mutable state belongs under the runtime data directory.

## Runtime data layout

By default, the runtime data root is the repository root and mutable files live beneath data/. Set LIKEPILOT_DATA_DIR to use a separate root; the same subdirectory layout is used beneath that path.

| Path | Purpose |
| --- | --- |
| data/config/config.json | Non-secret application configuration |
| data/config/.env | Local environment overrides |
| data/config/credential.key | Fernet key for encrypted SQLite credentials |
| data/config/dashboard-session.key | Persistent Flask session-signing key when FLASK_SECRET_KEY is not configured |
| data/database/likepilot.db | Canonical SQLite database |
| data/state/agents.json | Legacy agent seed; imported only when the agents table is empty |
| data/state/stats.json | Legacy statistics seed; imported only when credit history is empty |
| data/profiles/ | Persistent Chrome and Firefox browser profiles |
| data/logs/ | Runtime and session logs |
| data/diagnostics/ | HTML and screenshot captures |
| data/backups/ | Backup archives |
| data/tmp/ | Temporary update and restore files |

The legacy database name data/database/likeit.db is moved to likepilot.db when the canonical database does not yet exist. The old filename is retained as a compatibility input, not as a second active database.

## Canonical SQLite schema

### settings

| Column | Type | Meaning |
| --- | --- | --- |
| key | TEXT PRIMARY KEY | Setting identifier |
| value | TEXT NOT NULL | Serialized setting value; credential values use the enc:v1: encrypted representation |

Known key families include auto_switch, provider_login.<provider>.*, and secret.*. Application secrets are encrypted before persistence. Provider usernames and enabled flags are not secret values.

### agents

| Column | Type | Meaning |
| --- | --- | --- |
| name | TEXT PRIMARY KEY | Agent identifier |
| chrome_profile | TEXT NOT NULL | Persistent browser profile name |
| proxy | TEXT | Agent proxy configuration; encrypted at rest when non-empty |
| login_user | TEXT | Legacy per-agent login username |
| login_password | TEXT | Legacy per-agent password; encrypted at rest and omitted from general agent reads |
| enabled | INTEGER NOT NULL DEFAULT 0 | Saved enabled flag |
| status | TEXT NOT NULL DEFAULT 'Stopped' | Runtime state |
| credits | INTEGER NOT NULL DEFAULT 0 | Latest known credits |
| site | TEXT NOT NULL DEFAULT 'Like4Like' | Assigned provider |
| platform | TEXT NOT NULL DEFAULT 'Twitter' | Assigned social platform |
| fallback_platform | TEXT | Optional fallback platform |
| fallback_chain | TEXT | Serialized fallback sequence |
| comment_templates | TEXT | Optional custom comment templates |
| switch_pending | INTEGER NOT NULL DEFAULT 0 | Pending platform-switch flag |
| switch_reason | TEXT | Reason for a pending switch |
| last_error | TEXT | Last runtime error, with log redaction applied |
| heartbeat_at | TEXT | Latest worker heartbeat |
| session_started_at | TEXT | Current session start timestamp |
| updated_at | TEXT NOT NULL | Last update timestamp |
| created_at | TEXT NOT NULL | Creation timestamp |

The startup migration adds missing columns to older agents tables with ALTER TABLE. It does not drop existing columns or tables.

### agent_logs

| Column | Type | Meaning |
| --- | --- | --- |
| id | INTEGER PRIMARY KEY AUTOINCREMENT | Log row identifier |
| agent_name | TEXT NOT NULL | Agent that emitted the event |
| level | TEXT NOT NULL | Event severity |
| message | TEXT NOT NULL | Redacted event text |
| created_at | TEXT NOT NULL | Event timestamp |

Logs are capped per agent by the state layer. Existing log rows are scrubbed when read, but existing raw values are not rewritten automatically.

### credit_history

| Column | Type | Meaning |
| --- | --- | --- |
| id | INTEGER PRIMARY KEY AUTOINCREMENT | History row identifier |
| agent_name | TEXT | Associated agent, when known |
| platform | TEXT NOT NULL | Platform associated with the credit sample |
| credits | INTEGER NOT NULL | Recorded credit total |
| created_at | TEXT NOT NULL | Sample timestamp |

## Migration behavior

1. Path resolution creates the target data directories. Legacy root-level runtime files are moved or copied on first access. Tracked compatibility seeds are copied rather than removed; destination collisions are preserved.
2. If data/database/likepilot.db is absent and data/database/likeit.db exists, the legacy database is moved to the canonical filename.
3. Database initialization creates missing tables and adds missing agent columns. It then encrypts plaintext provider passwords, legacy agent passwords, and per-agent proxy credentials already in SQLite.
4. Legacy agents.json and stats.json are imported only when their corresponding SQLite tables are empty.
5. CAPTCHA API keys, authenticated proxy-list entries, Discord webhook URLs, and Telegram bot tokens are migrated lazily when their respective configuration accessors are first used. The old JSON values are cleared after the encrypted SQLite value is written.
6. Browser profiles are migrated individually to data/profiles/ when first opened. A destination collision stops migration rather than overwriting either copy.

Migrations are designed to be additive and non-destructive. Do not manually delete legacy files or database copies until the running installation has been verified and a backup exists.

## Backup and restore

Backups use SQLite's online backup API for a consistent database snapshot, then package supported config/state files, credential and dashboard session-signing keys, and logs into a verified ZIP archive. Restore validates archive paths and JSON/SQLite integrity before replacing files.

Stop the LikePilot server and all agent workers before restoring. Restore the database and its matching credential key together. Restore the runtime .env file and session key with the same backup set. Backup archives contain sensitive material and must be protected accordingly.

A backup/restore cycle against a user's live data directory is an operational verification step and is not replaced by automated fixture tests.
