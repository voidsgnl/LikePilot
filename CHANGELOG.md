# Changelog

## Unreleased

- Documented the canonical SQLite schema, runtime data layout, additive migration behavior, legacy import rules, credential/profile migrations, and backup/restore requirements in docs/architecture/persistence.md.

- Removed the built-in dashboard password fallback. Existing strong DASHBOARD_PASS overrides remain supported; otherwise a unique password and persistent Flask session key are created under data/config with owner-only permissions. Included both files in backup/restore, hardened session cookies and rotation, added failed-login throttling, and kept the default dashboard bind address local. Added dashboard security and recovery documentation; local login and HTTPS validation remain pending.

- Disabled the in-place updater installer and removed its unverified ZIP extraction/direct source-overwrite path. Release checks remain available, but updates must be installed manually until signed package verification and atomic rollback-safe staging are implemented.

- Migrated authenticated proxy entries, Discord webhook URLs, and Telegram bot tokens from legacy JSON configuration into encrypted SQLite settings. Plaintext config values are cleared after successful migration, and proxy-list updates remain encrypted. Added notification defaults so existing notification settings survive configuration merging; GitHub Actions passed 56 tests on Python 3.14.
- Added centralized log redaction for registered runtime secrets, credential-bearing URLs, authorization headers, sensitive query parameters, Discord webhook URLs, and Telegram bot tokens. Applied it to console/file logs, persisted agent logs, agent error state, notification error details, and outbound notification payloads; older agent-log entries are scrubbed when read. GitHub Actions passed 60 tests on Python 3.14. New page diagnostics now mask password, hidden, token, CSRF, and API-key form values in HTML and screenshots, and use owner-only directory/file permissions where supported. Existing log and diagnostic files are not rewritten; review of legacy artifacts remains open.

- Added Fernet authenticated encryption for provider passwords and legacy agent passwords stored in SQLite, with automatic migration of existing plaintext rows. General agent reads no longer expose the legacy password column; provider settings APIs continue to return only password-presence metadata. CAPTCHA API keys are migrated from legacy JSON configuration into encrypted SQLite settings. The encryption key is stored separately at `data/config/credential.key` with owner-only permissions where supported, fails closed if missing, and is preserved in backup archives. Backup archives therefore contain sensitive key material and must be protected. Removed the obsolete optional `encrypt_credentials` toggle. Per-agent proxy credentials are encrypted at rest in SQLite, with automatic migration of legacy plaintext proxy columns. Authenticated proxy-list entries, Discord webhook URLs, and Telegram bot tokens are also migrated from JSON configuration into encrypted SQLite settings on first use; proxy-list changes are persisted encrypted. Their dedicated migration tests are included. Actual migration against the user's local configuration remains pending.

- Audited persistence and runtime redundancy. `core/state.py` is the canonical persistence layer. The old `core/database.py` pointed to the same `data/database/likepilot.db` file and defined unused sessions/errors/snapshots tables; it and its only importer, the unreferenced mock `smart_timing.py`, have been removed. Existing SQLite tables and legacy timing-data files were not deleted. The dashboard still uses the `agents.py` facade; the unused `stats.py` facade has also been removed. The server explicitly starts the threaded supervisor; the dormant multiprocessing implementation, selector, and obsolete config keys have been removed. An unreferenced performance-monitor prototype and its `psutil` dependency were removed because no application path consumed its telemetry. `legacy/advanced_bot.py` has no active imports or launcher references and remains isolated as a historical prototype.


- Removed the unused statistics facade, dormant multiprocessing supervisor and selector, obsolete multiprocessing configuration, and unreferenced performance-monitor prototype. Removed the now-unused `psutil` dependency and stale performance/smart-timing options from default and seed configuration. Existing user config files are not rewritten; obsolete keys are simply ignored. Updated SQLite state timestamps to use timezone-aware UTC and removed the Python 3.14 `utcnow()` deprecation warning. Removed the unused WebSocket configuration switch/helper and `eventlet` dependency; the dashboard continues to use its existing polling transport. Removed `webdriver-manager` and `colorama`, which were only imported by the archived legacy prototype. Kept `setuptools` in runtime dependencies because the current `undetected-chromedriver` release still imports `distutils`, which Python 3.14 no longer provides.

- Hardened SQLite backup/restore: backups now use SQLite's online backup API for a consistent snapshot and validate database integrity. Restore copies into a temporary database, checks integrity, then atomically replaces the live file; corrupt backups are rejected without overwriting existing data. Added regression tests for backup, successful restore, and corrupt-backup rejection. Completed ZIP archive verification, safe member-path validation, preflight JSON/SQLite integrity checks, atomic config/state replacement, and staged log-directory restore. Added end-to-end coverage for database, `.env`, JSON configuration/state, logs, and ZIP path-traversal rejection. GitHub Actions passes 46 tests on Python 3.14. Stop the server and agent workers before restoring; validation against the user's existing local data remains pending.

- Centralized runtime storage beneath `data/`: configuration and environment files, agent/statistics/timing state, SQLite databases, browser profiles, logs, diagnostics, backups, runtime metadata, and updater temporary files now have dedicated locations. Added first-use legacy migration that copies archived compatibility seeds from `legacy/runtime-seed/` and moves untracked files/directories without overwriting destination collisions; removed `config.json`, `agents.json`, and `stats.json` from the repository root while preserving old-checkout migration fallback; updated backup/restore, dashboard operations, provider diagnostics, console logging, and smart-timing paths. Added migration regression tests; GitHub Actions passed (39 tests). Local backup/restore and dashboard validation remain pending.


- Changed Chrome and Firefox persistent profile storage to `data/profiles/`. On first use, an existing matching profile under root `profiles/` is moved with an atomic same-filesystem rename, preserving cookies and session data. If both old and new profile directories exist, startup fails clearly without overwriting either copy. Added regression tests for new paths, legacy migration, and duplicate protection; CI verification pending.

- Recorded user confirmation that the migrated `python farm.py` startup path launches the dashboard successfully. Clean shutdown and clean-install verification remain pending.

- Recorded the remaining local-only legacy directories in the roadmap: cache-only `web/` and `modules/`, retired `tools/build/`, and persistent browser profiles reserved for the later `data/profiles/` migration. No local runtime data was moved or deleted.

- Extracted `Like4LikeBase` into `src/likepilot/integrations/providers/like4like.py`. Shared browser/session lifecycle behavior remains in `providers/base.py`; Facebook, Instagram, TikTok, X, and YouTube now import the Like4Like foundation from its dedicated module.

- Added shared task-window tracking and safe cleanup across Like4Like social-network tasks, KingdomLikes, and YouLikeHits YouTube tasks. Social task windows now remain open through provider confirmation and a confirmed credit increase (polled for up to 20 seconds); the shared close helper blocks premature closure and restores focus to the provider window. Failed or unverified tasks leave their task window open for recovery. Added regression tests for new-window detection, close gating, and focus restoration; live provider/browser validation remains pending.

- Added system-level provider login settings for Like4Like, KingdomLikes, and YouLikeHits. Each provider has independent credentials and an Auto login switch inherited by all assigned agents; disabled mode remains manual, and verification challenges fall back to manual completion. Removed per-agent provider credential controls and refreshed the service-worker cache to v1.0.15. Added provider-settings persistence and dashboard regression tests; GitHub Actions passed (24 tests).

- Fixed Firefox agent startup by skipping the Chrome-only CDP stealth injection for Firefox; added regression coverage for Firefox and Chrome. Firefox continues through Selenium WebDriver without CDP commands.

- Fixed Firefox startup on Ubuntu Snap installations by resolving the executable inside the mounted Firefox Snap; added `LIKEPILOT_FIREFOX_BINARY` for explicit executable overrides. Chrome startup behavior is unchanged.

- Added a GitHub Actions workflow that installs LikePilot with development dependencies, compiles source/tests, and runs the full pytest suite on pushes to `main`, pull requests, and manual dispatch.

- Simplified Analytics, Create Agent, Manage Agents, and Browser Settings by removing repeated headings, decorative labels, redundant descriptions, and initial loading copy; corrected the historical chart label and refreshed the service-worker cache to v1.0.14.

- Restricted Operations → Database to schema metadata only (tables, columns, nullability, primary/foreign keys, and indexes); removed row previews and the table-data API. Bumped the service-worker cache to v1.0.13.

- Centered and simplified the login screen; removed redundant navigation/page copy; disabled decorative dashboard motion and stabilized header/overview loading space. Updated service-worker cache to v1.0.12.

- Made empty Analytics history explicit with em-dash metric values, removed dormant hard-coded forecast data, tightened Analytics wording, and removed the duplicate Operations heading/tagline.

- Removed the redundant header session summary and local clock; kept the live connection state and agent quick switch. Tightened Overview/Agents wording, corrected browser-profile fallback in the directory, and bumped the service-worker cache to v1.0.11.

- Fixed the Overview refresh indicator target and simplified the Agent directory empty state so empty inventories and unmatched filters have distinct, non-duplicated messages. Bumped the service-worker cache to v1.0.10.


- Refined individual agent workspaces: show only state-appropriate controls, separate runtime timestamps from saved profile details, remove low-value Session Peak/Samples metrics, and correct the Manage Agents destination. Bumped the service-worker cache to v1.0.9.

- Simplified dashboard content: removed duplicate Overview shortcuts and directory metrics, trimmed agent configuration pages, and removed static provider/platform catalogs from primary navigation while preserving integration code and routes.
- Reduced Analytics navigation to available views, moved Chart.js loading to Analytics only, and refreshed the service-worker cache to v1.0.8.
- Reduced theme choices to Dark, Light, and High Contrast; legacy theme preferences are normalized to Dark.
- Changed notification rendering to use text nodes so message content is not interpreted as HTML.

- Fixed the shared workspace grid: the navigation backdrop no longer occupies the main content column; bumped the service-worker cache to refresh the corrected stylesheet.

- Removed superseded `index.html` and `settings.html` templates after confirming that no active Flask route renders them.

- Started the full dashboard information-architecture redesign: a searchable agent directory, dedicated per-agent workspaces, provider and platform catalogs, and direct Operations subpages. Existing Flask APIs and runtime data remain the source of truth.
- Added per-agent runtime controls for start, ready, initialize, pause, resume, stop, and pending platform selection; recent events use the existing runtime log format.
- Split Analytics into dedicated routes for summary, trends, platforms, heatmap, insights, and export; split Settings into browser, create-agent, and manage-agent pages; Operations now loads only its selected workspace.
- Replaced the placeholder-heavy overview with a compact, live API-backed runtime summary; added responsive mobile navigation and direct quick-agent links to each agent workspace.

- Introduced a shared dashboard theme inspired by msf-web-console: compact dark surfaces, restrained green accents, consistent controls, and responsive navigation.

- Standardized the product on a single browser-accessed web application.
- Introduced the src-layout Python package and a single server entrypoint.
- Removed desktop-window wrappers and executable-build workflows from the target product.
- Preserved existing runtime data locations during the initial code migration.
