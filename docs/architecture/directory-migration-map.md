# Directory Migration Map

**Status:** Active src-layout migration  
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
├── data/                           # reserved; runtime-data migration pending
│   └── .gitkeep
└── legacy/
    └── advanced_bot.py              # isolated prototype; review separately
```

The future runtime-data directory is reserved but not yet activated. Existing root-level `config.json`, `agents.json`, `stats.json`, `runtime_port.txt`, databases, profiles, logs, and backups are preserved until the dedicated data migration is implemented.

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
- The runtime root remains the repository root in a source checkout so existing user data is not silently relocated. `LIKEPILOT_DATA_DIR` can explicitly override that root.

## Data-preservation rules

1. Do not move or delete the existing root-level database, config, agents, stats, profiles, logs, or backups during source migration.
2. Keep the current runtime root stable until configuration precedence and every data reader/writer are mapped.
3. Before introducing `data/`, implement a one-time, non-destructive migration with backups and compatibility fallback.
4. Verify database initialization, legacy JSON import, backup/restore, and dashboard operations after any data-path change.

## Verification gates

- [x] Inventory original tracked source, integration, dashboard, and launcher files.
- [x] Establish the web-only product decision and remove desktop from the target tree.
- [x] Add package metadata and a package-backed server entrypoint.
- [x] Move core, provider, network, and dashboard source into the src layout.
- [ ] Run package imports in a clean virtual environment.
- [ ] Run the structural test suite.
- [ ] Start the migrated server with `python farm.py` and verify browser login.
- [ ] Verify dashboard assets, routes, and agent lifecycle.
- [ ] Complete runtime-data migration separately, with backup/restore validation.

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
