# LikePilot Roadmap

**Project status:** Working web application; active restructuring and verification  
**Primary branch:** `main`  
**Delivery model:** One browser-accessed web application. Desktop applications and executable builds are not supported.  
**Roadmap policy:** Update task status only when the stated acceptance checks have actually passed.

LikePilot is a multi-platform automation and agent-management application. It connects engagement/task providers with social networks; Like4Like is one provider, not the product identity. The project is intended for educational, experimental, and software-development use. Users are responsible for complying with connected services' terms and automating only accounts and environments they are authorized to use.

## Product decisions

- **One product and one delivery model:** Python web server plus browser dashboard.
- **No desktop app or executable:** no pywebview shell, WebView2 runtime, PyInstaller workflow, desktop dependency group, or alternate desktop launcher.
- **One canonical start command:** `python farm.py`; the root launcher delegates to the packaged server entrypoint.
- **Package layout:** `src/likepilot`, with core, integrations, dashboard, and entrypoints separated.
- **Integration boundaries:** provider and social-network code are placed in distinct package areas. Existing adapters are preserved with minimal logic changes during the move.
- **Data protection:** existing databases, config, agent files, profiles, logs, and backups remain in their current locations until a separate data-path migration is designed and verified.
- **Working branch:** `main`; no feature branches unless explicitly requested.

## Status key

- [ ] Not started
- [~] In progress
- [x] Completed and verified
- [!] Blocked / decision required

## Phase 0 — Runtime integrity

- [x] **P0.1 — Restore and statically reconcile integration source.**
  - Confirm the eight integration source files are present.
  - Match the classes imported by the runtime with their definitions.
  - **Evidence:** static source reconciliation completed. Runtime execution remains separately tested.
- [~] **P0.2 — Establish the canonical web startup path.**
  - [x] Confirm `farm.py` starts the browser-accessed Flask server in the pre-migration checkout.
  - [x] Select `python farm.py` as the one documented launch command.
  - [ ] Verify the new package-backed launcher after the src-layout migration.
  - [ ] Verify clean shutdown and server error reporting.
  - **Acceptance:** a clean checkout installs and starts through the single documented command.
- [~] **P0.3 — Dependency and import audit.**
  - [x] Add project metadata and declare web/runtime dependencies in `pyproject.toml`.
  - [x] Remove desktop dependencies from the target install model.
  - [ ] Verify all imports against declared dependencies in a clean virtual environment.
  - [ ] Confirm supported Python/browser combinations.
  - **Acceptance:** clean install, imports, and server startup pass without desktop libraries.

## UI refinement — Login and loading stability

- [x] Center the login form and remove the promotional feature copy and redundant session footnote.
- [x] Remove repeated navigation descriptions and page subtitles from the shared dashboard shell.
- [x] Disable decorative entrance, pulse, glow, and hover movement that made page transitions feel unstable.
- [x] Reserve header and quick-switch space; remove the initial loading label and dashboard table loading message to reduce layout shift.
- [ ] Verify the centered login layout and stable page transitions in Firefox.

## Phase 1 — Source layout and redundancy

- [x] **P1.1 — Inventory the original root-level files and runtime responsibilities.**
- [x] **P1.2 — Define the src-layout target architecture before moving code.**
- [~] **P1.3 — Migrate source packages.**
  - [x] Move core modules under `src/likepilot/core/`.
  - [x] Move provider foundations and provider-specific adapters under `src/likepilot/integrations/providers/`.
  - [x] Move social-network adapters under `src/likepilot/integrations/networks/`.
  - [x] Move Flask application and its templates/static/favicon assets under `src/likepilot/dashboard/`.
  - [x] Move server implementation under `src/likepilot/entrypoints/`; retain `farm.py` as a small compatibility launcher.
  - [ ] Verify imports, package installation, static assets, templates, and startup after the move.
- [ ] **P1.4 — Complete runtime-data migration.**
  - [ ] Define the canonical data directory and configuration precedence.
  - [ ] Add non-destructive migration/compatibility handling for current root-level files.
  - [ ] Move runtime-generated logs, profiles, database, backups, and diagnostics only after backup/restore tests.
  - **Acceptance:** existing user data is discovered and preserved after upgrade.
- [~] **P1.5 — Resolve redundancy and legacy code.**
  - [x] Remove obsolete `index.html` and `settings.html` templates after tracing active Flask routes to their dedicated replacements.
  - [ ] Compare `core/state.py` and `core/database.py` schema and callers.
  - [ ] Review agent/statistics facades and both supervisor implementations.
  - [ ] Review `legacy/advanced_bot.py`; retain or remove based on an explicit usage decision.
  - **Acceptance:** each consolidation/removal has traced callers and regression coverage.

## Phase 2 — Integration and agent reliability

- [ ] **P2.1 — Map provider/network/action combinations to concrete classes.**
- [ ] **P2.2 — Verify agent create, configure, start, pause, resume, stop, restart, and delete flows.**
- [~] **P2.3 — Verify browser/profile/driver lifecycle and task result validation.**
  - [x] Add global dashboard browser selection (Chrome/Firefox), defaulting to Chrome for existing installations.
  - [x] Add separate Chrome and Firefox driver construction with browser-specific persistent profiles.
  - [x] Detect the executable inside Ubuntu's Firefox Snap and support `LIKEPILOT_FIREFOX_BINARY` as an explicit override.
  - [x] Restrict the existing CDP stealth injection to Chrome; Firefox skips CDP-only commands.
  - [ ] Verify Firefox startup with local Firefox/GeckoDriver and agent lifecycle on the user machine.
  - [ ] Verify Chrome regression and proxy behavior for both browsers.
- [ ] **P2.4 — Select and verify the runtime concurrency model.**
- [~] **P2.6 — Centralize task-window lifecycle and point-collection sequencing.**
  - [x] Add shared window tracking and lifecycle helpers to the common provider base; identify newly-created windows and restore focus to the provider window.
  - [x] Keep task windows open while social actions or provider confirmation are incomplete; avoid refreshing the task flow during recovery.
  - [x] Verify the social action before attempting provider confirmation.
  - [x] Poll and persist provider credits for a confirmed increase (up to 20 seconds) before allowing task-window closure; the shared close helper rejects calls without explicit credit-collection confirmation.
  - [x] Close the task window only after credit collection succeeds, then restore focus to the provider window.
  - [x] Add regression tests for new-window detection, premature-close prevention, and focus restoration.
  - [ ] Verify the full task/confirmation/credit sequence live against each provider and supported browser; browser-dependent validation remains.
  - **Acceptance:** task windows remain available until the social action and provider point collection are confirmed; cleanup happens afterward without ending the main browser session.
- **Acceptance:** each advertised integration and agent transition is verified and failures are visible.

- [~] **P2.5 — Add system-level provider login configuration.**
  - [x] Store independent Auto login mode and credentials for Like4Like, KingdomLikes, and YouLikeHits.
  - [x] Add a shared Provider login settings page; agents inherit the setting from their assigned provider.
  - [x] Remove provider credentials from agent creation and editing.
  - [x] Submit recognized provider login forms when enabled; retain manual login when disabled or when verification is required.
  - [x] Add persistence and dashboard-structure regression tests.
  - [ ] Verify login selectors and successful/manual fallback behavior against each provider in Firefox and Chrome; persistence and dashboard tests pass in CI (24 passed).
  - [ ] Complete credential-at-rest hardening under P4.3.
  - **Acceptance:** each provider can be independently configured once and every assigned agent follows that provider's login mode.

## Phase 3 — Browser dashboard

- [~] **P3.1 — Restructure dashboard information architecture and page layout.**
  - [x] Separate the searchable agent directory from individual agent detail URLs.
  - [x] Add dedicated provider and social-platform catalog pages.
  - [x] Add direct Operations destinations for database, logs, and diagnostics.
  - [x] Split Analytics into dedicated summary, trends, platforms, heatmap, insights, and export pages.
  - [x] Split Settings into browser, add-agent, and manage-agent pages.
  - [x] Make the dashboard overview the default landing page and remove duplicate shared script loading.
  - [x] Add source-level regression tests for workspace routes, page templates, and truthful analytics placeholders.
  - [ ] Verify all new page routes and browser rendering locally.
  - [x] Remove random heatmap samples and hard-coded forecast/insight claims; show explicit unavailable states until real telemetry exists.
  - [x] Split browser settings, agent creation, and agent configuration management into dedicated pages.
  - [x] Make Operations render and load only the selected database, logs, or diagnostics workspace.
  - [x] Replace the placeholder-heavy overview with a compact live runtime summary.
  - [x] Add responsive mobile navigation and repair the shared navigation markup.
  - [ ] Verify responsive navigation, page state, and all existing actions.
- [ ] **P3.1a — Audit dashboard controls against backend behavior.**
- [~] **P3.2 — Verify settings persistence and validation.**
  - [x] Add authenticated API endpoints and dashboard control for global browser selection.
  - [ ] Verify persistence and invalid-value rejection in the local dashboard.
- [~] **P3.3 — Improve agent status, activity, analytics, and error visibility.**
  - [x] Add a dedicated per-agent detail workspace with status, controls, configuration summary, and recent events.
  - [ ] Verify all controls and status refresh behavior locally.
- [ ] **P3.4 — Verify the browser dashboard across supported browsers and screen sizes.**
  - [ ] Verify the completed content cleanup in Firefox and Chrome.
  - [ ] Run the full test suite and fix any regressions.
- **Acceptance:** visible controls map to working backend behavior with clear success, empty, loading, and error states.

## Phase 3.5 — Dashboard content cleanup

- [x] **P3.5.1 — Remove duplicate and low-value page content.**
  - [x] Remove Overview shortcuts that duplicate primary navigation.
  - [x] Remove repeated summary metrics and low-value columns from the agent directory.
  - [x] Simplify Create Agent and Manage Agents panels by removing repeated headings, nested cards, and redundant links.
  - [x] Remove static provider/platform catalogs from primary navigation without deleting their adapters or routes.
  - [x] Keep unavailable Heatmap and Insights views out of the Analytics navigation until their telemetry exists.
  - [x] Load Chart.js only on Analytics pages and refresh the service-worker cache.
  - [x] Reduce theme choices to Dark, Light, and High Contrast while normalizing legacy saved theme values.
  - [x] Render notification text as text content rather than interpolated HTML.
  - [x] Restore the Overview refresh timestamp target so successful polling does not throw a missing-element error.
  - [x] Use one contextual empty row in the agent directory instead of duplicating the no-results message.
  - [x] Remove the redundant global session summary and local clock; retain the actionable agent quick switch and live connection indicator.
  - [x] Tighten Overview, Agents, and Analytics descriptions; display browser-neutral profile labels in the directory.
  - [x] Show unavailable analytics metrics as “—” when no credit snapshots exist; remove dormant hard-coded forecast data.
  - [x] Remove the Operations panel header that repeated the page title and added non-functional guidance.
  - [x] Restrict Database to schema metadata only: tables, columns, constraints, foreign keys, and indexes; remove row previews and the table-data API.
  - [x] Remove repeated headings, decorative labels, and redundant explanatory copy from Analytics and agent/browser settings pages.
- [~] **P3.5.2 — Refine agent workspace controls and information density.**
  - [x] Show only the action appropriate to the current agent state: Start, Ready, Initialize, Pause, Resume, or Stop.
  - [x] Separate heartbeat/session timestamps from saved profile configuration.
  - [x] Keep Credits and Session Gain as the primary agent metrics; remove Session Peak and Samples from the workspace.
  - [x] Correct the configuration link to open Manage Agents rather than Browser Settings.
  - [ ] Verify each status transition and platform-switch flow in the running dashboard.

## Phase 4 — Security and operations

- [ ] **P4.1 — Document persistence schemas and migration strategy.**
- [ ] **P4.2 — Verify backup, restore, and corruption recovery.**
- [ ] **P4.3 — Secure credential storage and remove insecure defaults.**
- [ ] **P4.4 — Prevent secrets from appearing in logs and diagnostics.**
- [ ] **P4.5 — Harden or disable unsafe updater installation behavior.**
- [ ] **P4.6 — Review dashboard authentication, sessions, and network exposure.**

## Phase 5 — Web installation and portability

- [x] **P5.1 — Remove desktop delivery from product scope.**
  - [x] Retire desktop-window wrappers and desktop-specific launchers from the repository.
  - [x] Remove executable packaging and desktop build workflow from the target architecture.
  - [x] Keep desktop-only dependencies out of the project install.
- [~] **P5.2 — Establish the source installation workflow.**
  - [x] Add `pyproject.toml` and editable installation metadata.
  - [x] Provide the web/runtime dependency declaration.
  - [x] Add `.env.example` and web-only setup instructions.
  - [ ] Verify clean installation and startup from a fresh checkout.
- [ ] **P5.3 — Verify Windows and Linux source workflows.**
  - [ ] Test browser driver and system-library requirements on each claimed platform.
  - [ ] Document tested platform limitations.
- [ ] **P5.4 — Add web application validation and deployment automation.**
  - [ ] Add CI checks for imports, tests, and startup.
  - [ ] Define versioning and source-release notes.

## Phase 6 — Testing

- [~] **P6.1 — Establish a test layout and package-structure smoke test.**
- [ ] **P6.2 — Add unit tests for configuration, paths, state, and persistence.**
- [ ] **P6.3 — Add integration tests for server routes and agent lifecycle.**
- [ ] **P6.4 — Add browser/provider integration tests with controlled fixtures.**
- [~] **P6.5 — Add automated quality checks.**
  - [x] Add GitHub Actions to install the project and run compile checks plus the full pytest suite on pushes to `main`, pull requests, and manual dispatch.
  - [ ] Add linting, formatting, and dependency checks.

## Phase 7 — Documentation

- [x] **P7.1 — Document the web-only product direction and initial setup workflow.**
- [x] **P7.2 — Document the package layout and provider/network separation.**
- [ ] **P7.3 — Complete configuration, troubleshooting, and backup/restore guides.**
- [ ] **P7.4 — Keep architecture documentation aligned with the final migrated tree.**
- [ ] **P7.5 — Maintain changelog and release notes.**

## Audit register

| ID | Finding | Status | Next action |
|---|---|---|---|
| A-001 | Runtime integration imports must resolve after the package move. | [~] Static class mapping passed; post-move import test pending | Run clean-install import and runtime smoke tests |
| A-002 | Original root had mixed source, launchers, runtime data, and docs. | [~] Source moved into src layout; runtime data remains at root | Complete data migration separately |
| A-003 | State and secondary database responsibilities need reconciliation. | [ ] Open | Compare schema, path, callers, and migrations |
| A-004 | Runtime and multiprocessing supervisors overlap. | [ ] Open | Trace active selection and lifecycle |
| A-005 | Desktop wrappers and executable build path were unrelated to web operation. | [x] Removed from the supported architecture and repository migration | Keep the web install free of desktop-only dependencies |
| A-006 | Existing root-level config and runtime files may contain live state. | [~] Preserved intentionally | Migrate only with compatibility and backup tests |
| A-007 | Original silent launcher advertised the wrong port and used Windows-only flags. | [x] Retired | Use the canonical web-server command |
| A-008 | Browser driver was Chrome-only; legacy `distutils` import failed under Python 3.14. | [~] Added global Chrome/Firefox selection, Ubuntu Firefox Snap binary resolution, and browser-specific stealth handling; local lifecycle verification pending | Verify Firefox/geckodriver startup and agent lifecycle, then run Chrome regression |
| A-009 | Provider login credentials and mode were configured per agent despite shared provider accounts. | [~] Added per-provider settings, inherited runtime behavior, and manual fallback for verification; local provider-specific validation pending | Verify all provider login forms and complete credential-at-rest hardening |

## Change tracking

| Date | Change | Verification |
|---|---|---|
| 2026-11-05 | Established LikePilot as a single browser-accessed web application; desktop executable distribution is out of scope. | Product decision confirmed. |
| 2026-11-05 | Added the initial repository inventory and migration map. | Static inspection of tracked source, launchers, integrations, and runtime-data ownership. |
| 2026-11-05 | Confirmed `python3 farm.py` starts the existing web server before the src-layout migration. | User-reported successful startup; post-migration verification remains pending. |
| 2026-11-05 | Began src-layout migration and added package metadata, web-only setup documentation, and a structural smoke test. | Package-level checks are pending execution in a clean environment. |
| 2026-11-06 | Added a global dashboard browser setting and separate Chrome/Firefox driver paths; Chrome remains the default and its existing profile paths are preserved. | Static implementation complete; local API, Firefox startup, and browser lifecycle checks pending. |
| 2026-11-06 | Restricted Chrome CDP stealth injection to Chrome so Firefox does not call Selenium's removed Firefox CDP implementation; added regression tests for both browser paths. | Source-level regression tests added; local Firefox startup and full suite execution pending. |
| 2026-11-06 | Added system-level provider login settings for Like4Like, KingdomLikes, and YouLikeHits; agents inherit the assigned provider's Auto login mode and credentials, with manual fallback for missing credentials or verification challenges. | GitHub Actions: 24 tests passed; live provider login validation remains pending. |


## Phase 8 — Dashboard visual system

- [~] **P8.1 — Align the LikePilot dashboard with the msf-web-console visual language.**
  - [x] Add a shared console theme stylesheet with the charcoal/green palette, compact surfaces, borders, controls, and typography.
  - [x] Restyle the navigation shell, top bar, common panels, tables, forms, buttons, badges, and login page.
  - [x] Restyle dashboard-specific metric and chart panels.
  - [x] Preserve LikePilot routes and application behavior while simplifying navigation, page content, and theme choices.
  - [ ] Verify all dashboard pages and responsive layouts in Firefox and Chrome.
  - [ ] Tune any page-specific layout regressions found during browser testing.
