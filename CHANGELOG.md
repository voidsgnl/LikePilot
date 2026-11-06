# Changelog

## Unreleased

- Added shared task-window tracking and safe cleanup across Like4Like social-network tasks, KingdomLikes, and YouLikeHits YouTube tasks. Social task windows now remain open through provider confirmation and a confirmed credit increase; the shared close helper blocks premature closure and restores focus to the provider window. Failed or unverified tasks leave their task window open for recovery. Added regression tests for new-window detection, close gating, and focus restoration; live provider/browser validation remains pending.

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
