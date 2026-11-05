# Changelog

## Unreleased

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
