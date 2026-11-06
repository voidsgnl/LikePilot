# Directory Migration Map

**Status:** Active source and runtime-data migration  
**Branch:** `main`  
**Delivery model:** One browser-accessed web application; no desktop application or executable build.

This map describes the target source layout and the migration status. Runtime data is deliberately not moved as part of the source-code move.

## Target directory tree

```text
LikePilot/
├── README.md
├── ROADMAP.md
├── CHANGELOG.md
├── pyproject.toml
├── requirements.txt
├── .env.example
├── .gitignore
├── .gitattributes
├── farm.py                         # compatibility launcher; canonical command
├── config/
│   ├── config.example.json
│   └── agents.example.json
├── src/
│   └── likepilot/
│       ├── __init__.py
│       ├── __main__.py
│       ├── core/
│       │   ├── __init__.py
│       │   └── runtime, state, config, paths, driver, and services
│       ├── integrations/
│       │   ├── __init__.py
│       │   ├── providers/
│       │   │   ├── __init__.py
│       │   │   ├── base.py
│       │   │   ├── kingdomlikes.py
│       │   │   └── youlikehits.py
│       │   ├── networks/
│       │   │   ├── __init__.py
│       │   │   ├── facebook.py
│       │   │   ├── instagram.py
│       │   │   ├── tiktok.py
│       │   │   ├── x.py
│       │   │   └── youtube.py
│       │   └── (provider/network adapter boundaries to be refined)
│       ├── dashboard/
│       │   ├── __init__.py
│       │   ├── app.py
│       │   ├── static/
│       │   ├── templates/
│       │   └── favicon/
│       └── entrypoints/
│           ├── __init__.py
│           └── server.py
├── docs/
│   ├── architecture/
│   ├── development/
│   └── user-guide/
├── tests/
├── data/                           # generated runtime data; contents are not committed
│   ├── config/                      # config.json and .env
│   ├── state/                       # agents.json, stats.json, timing data
│   ├── database/                    # SQLite databases
│   ├── profiles/                    # persistent Chrome/Firefox profiles
│   ├── logs/
│   ├── diagnostics/
│   ├── backups/
│   ├── runtime/                     # runtime_port.txt
│   └── tmp/                         # updater artifacts
└── legacy/
    └── advanced_bot.py              # isolated prototype; review separately
```

Runtime data is now routed beneath `data/`. On first access, known root-level legacy files and directories are migrated non-destructively. File migrations use atomic rename where possible; directory migrations move or merge non-conflicting entries. If a destination already exists, conflicting legacy entries remain at their original location and are never overwritten. Browser profiles retain their stricter duplicate-directory guard.

## Source migration mapping

| Original path | New path | Treatment |
|---|---|---|
| `core/*.py` | `src/likepilot/core/*.py` | Moved as a package; internal imports use `likepilot.core` |
| `modules/base.py` | `src/likepilot/integrations/providers/base.py` | Shared provider base classes |
| `modules/kingdomlikes.py` | `src/likepilot/integrations/providers/kingdomlikes.py` | KingdomLikes provider adapter |
| `modules/youlikehits.py` | `src/likepilot/integrations/providers/youlikehits.py` | YouLikeHits provider adapter |
| `modules/facebook.py` | `src/likepilot/integrations/networks/facebook.py` | Facebook actions currently implemented for Like4Like |
| `modules/instagram.py` | `src/likepilot/integrations/networks/instagram.py` | Instagram actions currently implemented for Like4Like |
| `modules/tiktok.py` | `src/likepilot/integrations/networks/tiktok.py` | TikTok actions currently implemented for Like4Like |
| `modules/twitter.py` | `src/likepilot/integrations/networks/x.py` | X/Twitter actions currently implemented for Like4Like |
| `modules/youtube.py` | `src/likepilot/integrations/networks/youtube.py` | YouTube actions currently implemented for Like4Like |
| `web/app.py` | `src/likepilot/dashboard/app.py` | Flask dashboard application |
| `web/static/*` | `src/likepilot/dashboard/static/*` | Dashboard static assets |
| `web/templates/*` | `src/likepilot/dashboard/templates/*` | Jinja templates |
| `web/favicon/*` | `src/likepilot/dashboard/favicon/*` | Favicon and web manifest assets |
| `farm.py` | `src/likepilot/entrypoints/server.py` | Server implementation; root `farm.py` remains as a compatibility launcher |
| `advanced_bot.py` | `legacy/advanced_bot.py` | Isolated standalone prototype; not imported by the active runtime |
| Desktop wrappers and launchers | Removed | `likepilot_desktop.py`, `dashboard_desktop.py`, `start_silent.py`, and desktop-specific batch/cmd launchers are not part of the product |
| Executable packaging | Removed from target | No PyInstaller, WebView2, or desktop build workflow |

## Package and startup conventions

- Package root: `src/likepilot`.
- Install: `python -m pip install -e .`.
- Canonical start: `python farm.py`.
- Package start: `python -m likepilot` or the installed `likepilot` console command.
- The root launcher adds `src/` to the import path and delegates to `likepilot.entrypoints.server`.
- Internal source imports use the `likepilot.*` namespace.
- Flask templates and static assets remain package-relative to the dashboard module.
- The runtime root remains the repository root in a source checkout; generated runtime files are placed under its `data/` child. `LIKEPILOT_DATA_DIR` overrides the runtime root and uses the same `data/` layout beneath it.

## Data-preservation rules

1. Runtime paths are centralized in `core/paths.py`; new runtime files belong beneath `data/`.
2. Legacy root-level files and directories are migrated only when their destination is absent; collisions preserve both copies.
3. Directory merges move only non-conflicting entries; conflicting files remain in the legacy directory for manual review.
4. Browser profiles use their dedicated atomic-migration and collision-protection flow.
5. Verify database initialization, legacy JSON import, backup/restore, and dashboard operations after any data-path change.

## Verification gates

- [x] Inventory original tracked source, integration, dashboard, and launcher files.
- [x] Establish the web-only product decision and remove desktop from the target tree.
- [x] Add package metadata and a package-backed server entrypoint.
- [x] Move core, provider, network, and dashboard source into the src layout.
- [ ] Run package imports in a clean virtual environment.
- [ ] Run the structural test suite.
- [ ] Start the migrated server with `python farm.py` and verify browser login.
- [ ] Verify dashboard assets, routes, and agent lifecycle.
- [x] Route runtime configuration, state, database, logs, diagnostics, backups, profiles, and transient files beneath `data/` with non-destructive legacy migration.
- [ ] Run the full test suite and validate database initialization, backup/restore, and dashboard operations locally.

## Known architectural constraints

- Some existing network action classes are provider-specific (currently Like4Like). They are placed in the network area for discoverability, but the provider/network boundary is not yet fully normalized. Do not rewrite adapter behavior as part of the filesystem move.
- `core/state.py` and `core/database.py` have overlapping persistence responsibilities. Preserve both until schema and callers are reconciled.
- Threaded and multiprocessing supervisors both exist. The canonical server currently starts the threaded supervisor; verify whether multiprocessing selection is intended before consolidating.
- The updater's file-copy model must be redesigned for a packaged src layout before updates are enabled.
- The standalone `advanced_bot.py` prototype remains isolated and is not part of the supported runtime.

## Change log

| Date | Change | Verification |
|---|---|---|
| 2026-11-05 | Replaced the earlier mixed desktop/web target with a single web-only src-layout map. | Product decision confirmed; implementation and post-move runtime checks tracked in ROADMAP.md. |
| 2026-11-06 | Centralized runtime paths beneath `data/` and added non-destructive migration of legacy files/directories, including collision preservation. | Regression tests added; full CI and local backup/restore validation pending. |
