# Credential storage and backup handling

LikePilot encrypts provider passwords, legacy agent passwords, CAPTCHA service API keys, authenticated proxy entries, Discord webhook URLs, and Telegram bot tokens before storing them in SQLite. Encryption uses Fernet authenticated encryption.

## Local key

The first encryption or legacy-credential migration creates `data/config/credential.key` with owner-only file permissions where supported. Keep this file private and do not delete it. LikePilot deliberately refuses to generate a replacement key when encrypted values already exist but the key is missing; generating a new key would make the existing credentials unrecoverable.

Legacy plaintext provider and agent passwords are encrypted automatically during database initialization. Legacy CAPTCHA API keys are moved from `data/config/config.json` into encrypted settings the first time the CAPTCHA integration loads them. Authenticated proxy entries are migrated the first time the proxy-list accessor is used; Discord webhook URLs and Telegram bot tokens are migrated when the notification manager initializes. The corresponding plaintext JSON values are cleared after successful migration. Proxy-list changes are persisted only in encrypted settings.

Authenticated proxy entries, Discord webhook URLs, and Telegram bot tokens are also encrypted in SQLite. Legacy values are migrated on first access and cleared from config.json; subsequent proxy-list changes remain encrypted.

The dashboard never returns saved passwords. Provider settings responses expose only whether a password is present. General agent reads omit the legacy agent password column. Runtime log output and outbound notification payloads apply secret redaction to registered credentials and common credential-bearing URL, authorization, and query-string formats. This reduces accidental disclosure but does not make it safe to include credentials in log messages. New page diagnostic captures mask password, hidden, token, CSRF, and API-key form values in HTML and screenshots; diagnostic files and their directory use owner-only permissions where supported. Existing console logs and diagnostic captures are not rewritten retroactively.

## Backups and restores

Backup archives include the credential key because the database cannot be restored usefully without it. This means backup archives contain material capable of decrypting the credentials inside them. Store backup archives as sensitive files, restrict access, and do not upload or share them.

Stop the LikePilot server and all agent workers before restoring. Restore the database, configuration, and credential key from the same backup set. Do not mix a database from one installation with another installation's key.

## Recovery limitation

If both the credential key and any independent copy of it are lost, encrypted credentials cannot be recovered. Restore the matching key from a protected backup. Do not delete or regenerate the key as a troubleshooting step.
