# Credential storage and backup handling

LikePilot encrypts provider passwords, legacy agent passwords, per-agent proxy credentials, CAPTCHA service API keys, authenticated proxy-list entries, Discord webhook URLs, and Telegram bot tokens before storing them in SQLite. Encryption uses Fernet authenticated encryption.

## Local key

The first encryption or legacy-credential migration creates `data/config/credential.key` with owner-only file permissions where supported. Keep this file private and do not delete it. LikePilot deliberately refuses to generate a replacement key when encrypted values already exist but the key is missing; generating a new key would make the existing credentials unrecoverable.

Legacy plaintext provider and agent passwords are encrypted automatically during database initialization. Legacy CAPTCHA API keys are moved from `data/config/config.json` into encrypted settings the first time the CAPTCHA integration loads them. Authenticated proxy entries are migrated the first time the proxy-list accessor is used; Discord webhook URLs and Telegram bot tokens are migrated when the notification manager initializes. The corresponding plaintext JSON values are cleared after successful migration. Proxy-list changes are persisted only in encrypted settings.

Per-agent proxy credentials are encrypted in the agents table, including automatic migration of existing plaintext proxy values. Authenticated proxy-list entries, Discord webhook URLs, and Telegram bot tokens are also encrypted in SQLite. Legacy values are migrated on first access and cleared from config.json; subsequent proxy-list changes remain encrypted.

The dashboard never returns saved passwords. Provider settings responses expose only whether a password is present. General agent reads omit the legacy agent password column. Runtime log output and outbound notification payloads apply secret redaction to registered credentials and common credential-bearing URL, authorization, and query-string formats. This reduces accidental disclosure but does not make it safe to include credentials in log messages. New page diagnostic captures mask password, hidden, token, CSRF, and API-key form values in HTML and screenshots; diagnostic files and their directory use owner-only permissions where supported. Existing console logs and diagnostic captures are not rewritten retroactively. Their directories and files are restricted to owner-only permissions where supported, log content is redacted when read through the dashboard, and HTML diagnostic content is sanitized when served. Existing PNG screenshots may still contain visible page content and should be reviewed before sharing.

## Backups and restores

Backup archives include the credential key and, when generated locally, the dashboard password and session key. The dashboard password file preserves access after restore, and the session key preserves session signing continuity. These files make backup archives sensitive; the credential key can decrypt stored credentials. On POSIX systems, LikePilot restricts its default backup directory to owner-only access and creates archive files with owner-only permissions. Restored `.env`, credential-key, dashboard-password, and session-key files are also restricted to owner-only access where supported. Store backup archives as sensitive files, and do not upload or share them.

Stop the LikePilot server and all agent workers before restoring. Restore the database, configuration, and credential key from the same backup set. Do not mix a database from one installation with another installation's key.

## Recovery limitation

If a generated dashboard password is forgotten and no copy is available, stop LikePilot, remove data/config/dashboard-password if it still exists, and restart; a new password is generated and its path is printed. Existing installations with an explicit DASHBOARD_PASS environment value continue to use that value. If both the credential key and any independent copy of it are lost, encrypted credentials cannot be recovered. Restore the matching key from a protected backup. Do not delete or regenerate the key as a troubleshooting step.
