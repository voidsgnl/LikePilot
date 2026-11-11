# Dashboard authentication and network security

LikePilot requires an explicitly configured dashboard password. It does not generate, rotate, or persist dashboard passwords. The password must contain 1–64 numeric digits.

## Configure dashboard access

Create or edit the runtime environment file:

    nano data/config/.env

Set the dashboard username and a numeric password using digits 0-9 (between 1 and 64 digits):

    DASHBOARD_USER=admin
    DASHBOARD_PASS=4827

Replace the example password with your own combination. Keep the file private; LikePilot restricts its permissions to the current owner where supported. Process-level environment variables take precedence over values in the runtime .env file.

The runtime environment file is located at data/config/.env by default. If LIKEPILOT_DATA_DIR points to a custom runtime root, place .env in that runtime root's config directory.

If DASHBOARD_PASS is missing or invalid, startup stops with a clear configuration error. The old data/config/dashboard-password file is no longer read. You may delete it after upgrading.

## Session signing

If FLASK_SECRET_KEY is not configured, LikePilot creates data/config/dashboard-session.key and reuses it across restarts. This is a separate high-entropy key used to sign Flask sessions; it is not the dashboard password. Protect it and include it in secure backups.

Login sessions use HTTP-only, SameSite=Lax cookies, an eight-hour lifetime, and session rotation on successful login. Failed login attempts are temporarily rate-limited per client address.

## Network exposure

The default dashboard bind address is 127.0.0.1. Keep it local unless remote access is deliberate. For remote access, use an HTTPS reverse proxy, firewall the application port, and set DASHBOARD_COOKIE_SECURE=true so browsers send the session cookie only over HTTPS. Do not expose the built-in HTTP server directly to an untrusted network.

The numeric vault is a convenience gate for a local-only application, not strong authentication for a shared or internet-facing service.
