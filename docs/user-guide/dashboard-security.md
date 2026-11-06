# Dashboard authentication and network security

LikePilot no longer has a built-in dashboard password.

## First startup

If DASHBOARD_PASS is not set to a strong explicit value, LikePilot creates a unique password and stores it in data/config/dashboard-password with owner-only file permissions. The server log prints the file path, not the password. Read the file locally to sign in:

    cat data/config/dashboard-password

Existing installations that already configure a non-placeholder DASHBOARD_PASS keep using it. The old built-in password is not accepted.

To rotate a generated password, stop LikePilot, remove data/config/dashboard-password, and start it again. A new password is generated. Do not delete this file if you still need the current password.

## Session signing

If FLASK_SECRET_KEY is not configured, LikePilot creates data/config/dashboard-session.key and reuses it across restarts. Both dashboard authentication files are included in backup and restore archives. Protect those archives as sensitive files.

Login sessions use HTTP-only, SameSite=Lax cookies, an eight-hour lifetime, and session rotation on successful login. Failed login attempts are temporarily rate-limited per client address.

## Network exposure

The default dashboard bind address is 127.0.0.1. Keep it local unless remote access is deliberate. For remote access, use an HTTPS reverse proxy, firewall the application port, and set DASHBOARD_COOKIE_SECURE=true so browsers send the session cookie only over HTTPS. Do not expose the built-in HTTP server directly to an untrusted network.

A configured DASHBOARD_PASS overrides the generated password file. Use a unique, high-entropy value and keep it out of shell history, screenshots, and logs.
