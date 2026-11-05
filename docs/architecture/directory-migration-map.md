# Directory Migration Map

**Status:** Draft mapping for the approved target architecture  
**Branch:** `main`  
**Rule:** This document is an inventory and migration plan, not authorization to move or delete files without the verification gates below.

## Target layout (single web delivery model)

```text
LikePilot/
├── README.md
├── ROADMAP.md
├── CHANGELOG.md
├── pyproject.toml
├── .gitignore
├── config/
│   ├── config.example.json
│   └── agents.example.json
├── src/
│   └── likepilot/
│       ├── __init__.py
│       ├── core/
│       ├── integrations/
│       │   ├── providers/
│       │   │   ├── like4like/
│       │   │   ├── kingdomlikes/
│       │   │   └── youlikehits/
│       │   └── networks/
│       │       ├── facebook/
│       │       ├── instagram/
│       │       ├── tiktok/
│       │       ├── x/
│       │       └── youtube/
│       ├── dashboard/
│       │   ├── app.py
│       │   ├── static/
│       │   ├── templates/
│       │   └── favicon/
│       ├── desktop/
│       ├── entrypoints/
│       └── services/
├── scripts/
│   ├── windows/
│   └── cross-platform/
├── packaging/
│   └── windows/
├── tests/
├── docs/
│   ├── architecture/
│   ├── development/
│   └── user-guide/
└── data/  # runtime-generated; excluded from version control
    ├── agents/
    ├── stats/
    ├── profiles/
    ├── logs/
    └── backups/
```

The `src/likepilot` layout requires a deliberate package/import migration. There is no desktop package or executable packaging area in the target architecture. Existing imports such as `from core...` and `from web...` must not be broken by moving files. We will either convert imports consistently to the package namespace and configure packaging, or retain temporary compatibility entrypoints during migration.

## Current tracked-file mapping

| Current path | Proposed destination | Initial disposition | Verification required |
|---|---|---|---|
| `core/*.py` | `src/likepilot/core/*.py` | Move as a group only after package/import plan | Inspect all imports, dynamic imports, resource paths, and external callers |
| `core/runtime.py` | `src/likepilot/core/runtime.py` | Retain; integration imports currently reference missing `modules/` | Resolve A-001 and map bot classes before moving |
| `core/multiprocess_runtime.py` | `src/likepilot/core/` (or runtime service package) | Retain pending runtime-selection audit | Trace configuration, process state, and actual callers |
| `core/agents.py`, `core/stats.py` | `src/likepilot/core/` initially | Retain pending redundancy audit | Confirm compatibility callers before any consolidation |
| `web/app.py` | `src/likepilot/dashboard/app.py` | Move after import and resource-path migration | Update imports, templates/static paths, favicon paths, and desktop launchers |
| `web/static/*` | `src/likepilot/dashboard/static/*` | Move with dashboard as one asset group | Check Flask static configuration and every asset URL |
| `web/templates/*` | `src/likepilot/dashboard/templates/*` | Move with dashboard as one asset group | Check Flask template loader and template inheritance |
| `web/favicon/*` | `src/likepilot/dashboard/favicon/*` | Move with dashboard assets | Check `bundle_path` and favicon route |
| `farm.py` | `src/likepilot/entrypoints/server.py` | Keep as primary server entrypoint candidate | Confirm intended primary launch mode and preserve compatibility command |
| `likepilot_desktop.py` | `src/likepilot/entrypoints/desktop.py` or desktop package | Keep as desktop entrypoint candidate | Verify pywebview lifecycle and server ownership |
| `dashboard_desktop.py` | `src/likepilot/entrypoints/dashboard_desktop.py` initially | Retain until overlap is understood | Compare behavior with `likepilot_desktop.py`; do not merge by name alone |
| `start_silent.py` | `scripts/windows/start_silent.py` plus a separately tested cross-platform launcher if required | Windows-specific launcher candidate | Fix port/help text and verify process detach/stop behavior |
| `run_*.cmd`, `run_background.bat` | `scripts/windows/` | Move after inspecting their contents | Check referenced paths, working directory, quoting, and packaged/source modes |
| `requirements.txt` | Dependency declarations in `pyproject.toml` | Replace only after dependency audit | Separate core, desktop, optional, and development dependencies; verify platform markers |
| `config.json` | Runtime config under `data/`; sanitized template under `config/config.example.json` | Preserve current user settings; do not blindly rename into an example | Trace config loader, precedence, defaults, and migration behavior |
| `agents.json` | Runtime agent data under `data/agents/`; sanitized template only if needed | Preserve current data; do not treat as disposable sample | Trace whether current runtime reads this file or uses SQLite instead |
| `stats.json` | `data/stats/` or remove from tracked tree only after proving generated/unused | Preserve until ownership is known | Trace readers/writers and migration/backup requirements |
| `runtime_port.txt` | `data/` runtime status output | Generated-file candidate | Confirm all writers/readers and ignore policy |
| `advanced_bot.py` | `legacy/` (temporary) or remove after review | Do not include in active package yet | Determine whether any launcher or documented workflow uses it |
| `README.md`, `ROADMAP.md` | Repository root | Keep | Update documentation after behavior and final paths are verified |
| `.gitignore`, `.gitattributes` | Repository root | Keep | Extend ignore rules only after runtime data locations are finalized |
| `requirements.txt` | Root temporarily, then package metadata | Keep during transition | Avoid breaking existing install instructions before replacement is tested |

## Missing or not-yet-mapped content

- `modules/` is now present in remote `main` with `base.py`, `facebook.py`, `instagram.py`, `tiktok.py`, `twitter.py`, `youtube.py`, `kingdomlikes.py`, and `youlikehits.py`. Runtime import names have been statically checked against class definitions; clean-checkout import and startup tests remain pending.
- The current GitHub tree contains no tracked `tests/`, `docs/`, `pyproject.toml`, or `CHANGELOG.md`. These are planned additions, not existing files to move.
- The current root `config.json`, `agents.json`, and `stats.json` need runtime ownership checks before they are classified as templates, live state, or obsolete artifacts.

## Migration gates

1. **Complete inventory:** inspect every tracked file, including all launch scripts and runtime configuration/path helpers.
2. **Resolve runtime blockers:** establish the source of the missing integration package and verify a clean checkout's import path.
3. **Package decision:** settle the canonical package namespace, module entrypoints, resource lookup strategy, and compatibility period.
4. **Data protection:** identify live state files and database locations; add backup/restore checks before changing paths.
5. **Move in groups:** core package, integrations, dashboard/assets, entrypoints/scripts, then configuration and packaging.
6. **Verify after each group:** run import checks, focused tests, startup smoke tests, and path/resource checks before continuing.
7. **Cleanup last:** remove compatibility wrappers or old paths only when all supported launch paths have passed verification.

## Initial findings that affect the mapping

- `core/runtime.py` imports classes from the now-tracked `modules/` package. The source is available, but clean-checkout import and runtime behavior still need verification.
- `farm.py` imports `core.runtime` and `web.app`; the desktop entrypoints also import these top-level packages.
- `web/app.py` imports `core.*` and resolves assets/templates relative to the current layout.
- `core/database.py` creates a SQLite database at a path derived from the current repository layout, while `core/state.py` has its own persistence implementation. Their relationship is not yet established.
- `core/agents.py` and `core/stats.py` are thin wrappers over `core.state`; preserve them until callers and compatibility expectations are checked.
- `core/multiprocess_runtime.py` starts workers that import `core.runtime`; moving package boundaries must account for multiprocessing importability and shared state.
- `farm.py` defaults to port 5001, while `start_silent.py` currently advertises port 5000.
- `config.json` contains a duplicate `performance` key and placeholder values. Normalize only after config precedence and live-user settings are understood.

## Change log

| Date | Change | Verification |
|---|---|---|
| 2026-11-05 | Created initial file-by-file migration map from the tracked repository tree and inspected entrypoints/core/dashboard paths. No application files moved or modified. | Static source inspection only; runtime and clean-checkout verification remain pending. |


## Verified tracked-file inventory (2026-11-05)

This inventory covers the complete 66-path GitHub tree on `main` at the time of review. It records proposed destinations, not permission to move live data or remove compatibility paths.

| Current path | Proposed destination | Notes / gate |
|---|---|---|
| `.gitattributes`, `.gitignore` | Repository root | Keep; revise ignore rules only when runtime data destinations are finalized. |
| `README.md`, `ROADMAP.md` | Repository root | Keep as project entry documentation and progress tracker. |
| `requirements.txt` | Web/runtime dependencies in `pyproject.toml` | Keep during transition; remove desktop-only dependencies and build requirements. |
| `config.json` | `data/config.json`; sanitized template at `config/config.example.json` | Existing file contains live-looking settings, a duplicate `performance` key, proxy placeholder, and updater placeholder. Preserve before migration. |
| `agents.json` | `data/agents.json` (or `data/agents/...` after schema decision) | `core/state.py` imports it only as legacy seed data when the SQLite agents table is empty. Preserve for migration compatibility. |
| `stats.json` | `data/stats.json` or archive after migration verification | `core/state.py` imports its history into SQLite only when credit history is empty. Preserve until migration is proven. |
| `runtime_port.txt` | `data/runtime_port.txt` | Generated by `farm.py`; path is currently runtime-root-relative. |
| `advanced_bot.py` | `legacy/advanced_bot.py` pending decision | Standalone Like4Like/Twitter prototype; no tracked import/caller found in search. It expects a local `cookies.json` and is not the current registry-driven runtime. |
| `farm.py` | `src/likepilot/entrypoints/server.py` | Current server entrypoint; owns bootstrap, health-checked Flask server, port selection and runtime-port file. |
| `likepilot_desktop.py` | Remove | Legacy desktop executable/window wrapper; desktop delivery is out of scope. |
| `dashboard_desktop.py` | Remove | Legacy desktop dashboard wrapper; not part of the sole browser-based product. |
| `start_silent.py` | Remove or replace with a cross-platform web-server launcher only if needed | Legacy Windows-specific launcher; its advertised port conflicts with `farm.py`. |
| `run_farm.cmd` | Keep only if it launches the canonical web server | Retire `run_background.bat`, `run_dashboard_desktop.cmd`, and `run_likepilot_desktop.cmd` as desktop-specific launchers. |
| `core/*.py` | `src/likepilot/core/*.py` | Move only after package namespace and compatibility import strategy are implemented. |
| `web/app.py` | `src/likepilot/dashboard/app.py` | Flask app; imports `core.*` and relies on current template/static paths. |
| `web/static/*` | `src/likepilot/dashboard/static/*` | Move with dashboard app; update Flask static configuration and URL references. |
| `web/templates/*` | `src/likepilot/dashboard/templates/*` | Move with dashboard app; preserve template inheritance and endpoint references. |
| `web/favicon/*` | `src/likepilot/dashboard/favicon/*` | Move with dashboard app; verify favicon and manifest routes. |
| `docs/architecture/directory-migration-map.md` | `docs/architecture/directory-migration-map.md` | Keep; update as decisions and migration stages complete. |

### Core module inventory

| Current file | Proposed destination | Current finding |
|---|---|---|
| `core/__init__.py` | `src/likepilot/core/__init__.py` | Preserve package marker if present in local checkout; it was not a tracked path in the audited tree. |
| `core/agents.py` | `src/likepilot/core/agents.py` initially | Thin facade over `core.state`; imported by `web/app.py`, so not safe to delete as an unused file. |
| `core/auto_updater.py` | `src/likepilot/services/updater.py` or `core/` | Service ownership and updater safety review required. |
| `core/backup_manager.py` | `src/likepilot/services/backup.py` | Uses runtime-root database path; update with data-path migration. |
| `core/captcha_solver.py` | `src/likepilot/services/captcha.py` | Optional external service integration; keep separate from platform/provider adapters. |
| `core/config.py` | `src/likepilot/core/config.py` | Loads `config.json` via `runtime_path`; path migration must preserve existing settings. |
| `core/console.py` | `src/likepilot/services/console.py` | Runtime logging setup; inspect imports before final placement. |
| `core/database.py` | `src/likepilot/core/database.py` temporarily | Separate SQLite schema; imported by `core.smart_timing`, but the timing implementation currently uses mock data rather than its DB object. Do not merge yet. |
| `core/driver.py` | `src/likepilot/core/driver.py` | Browser driver lifecycle; verify Selenium/undetected-chromedriver compatibility per platform. |
| `core/human_behavior.py` | `src/likepilot/services/automation/` | Supporting automation behavior; confirm callers and ownership. |
| `core/intelligence.py` | `src/likepilot/services/` | Inspect actual callers before choosing final service boundary. |
| `core/multiprocess_runtime.py` | `src/likepilot/core/multiprocess_runtime.py` temporarily | Has a configurable supervisor selector, but current `farm.py` and desktop entrypoint import the threaded supervisor directly. No active selector call was found in tracked code search. |
| `core/notifications.py` | `src/likepilot/services/notifications.py` | Supporting notification service; preserve configuration and secrets handling. |
| `core/paths.py` | `src/likepilot/core/paths.py` | Central path policy; must be redesigned before relocating runtime data. |
| `core/performance_monitor.py` | `src/likepilot/services/monitoring.py` | Supporting monitoring service; confirm actual call sites. |
| `core/portable.py` | `src/likepilot/core/portable.py` or `services/runtime_setup.py` | Creates runtime folders and portable files; coordinate with data-directory design. |
| `core/rate_limiting.py` | `src/likepilot/services/rate_limiting.py` | Supporting service; confirm call sites. |
| `core/runtime.py` | `src/likepilot/core/runtime.py` temporarily | Imports missing `modules.*` classes at module import time; blocks clean-checkout startup and package migration. |
| `core/smart_timing.py` | `src/likepilot/services/smart_timing.py` | Imports `core.database.db`; currently returns mock hourly patterns and writes a JSON file under current working directory. |
| `core/state.py` | `src/likepilot/core/state.py` | Primary active persistence layer for agents, logs, settings and credit history; also migrates legacy JSON data. |
| `core/stats.py` | `src/likepilot/core/stats.py` initially | Thin facade over `core.state`; no tracked internal import found, but preserve pending compatibility review. |

### Integration inventory (remote `main`, checked 2026-11-05)

The integration source is now tracked in `modules/`:

| Current file | Implementation role | Proposed migration treatment |
|---|---|---|
| `modules/base.py` | Shared bot abstractions: `BaseBot`, `Like4LikeBase`, `KingdomLikesBase`, `YouLikeHitsBase` | Move with integration adapters; preserve shared base contracts and avoid premature provider/network split |
| `modules/facebook.py` | Facebook actions built on `Like4LikeBase` | Treat as Like4Like-specific Facebook adapter; decide final provider/network placement after adapter contract review |
| `modules/instagram.py` | Instagram actions built on `Like4LikeBase` | Treat as Like4Like-specific Instagram adapter |
| `modules/tiktok.py` | TikTok actions built on `Like4LikeBase` | Treat as Like4Like-specific TikTok adapter |
| `modules/twitter.py` | X/Twitter actions built on `Like4LikeBase` | Treat as Like4Like-specific X/Twitter adapter |
| `modules/youtube.py` | YouTube actions built on `Like4LikeBase` | Treat as Like4Like-specific YouTube adapter |
| `modules/kingdomlikes.py` | KingdomLikes actions across several social networks | Treat as provider adapter; keep its network-specific action classes together initially |
| `modules/youlikehits.py` | YouLikeHits YouTube actions | Treat as provider adapter; keep its action classes together initially |

Static comparison of `core/runtime.py` imports and module class declarations found definitions for all imported class names. The files import `modules.base` and existing `core.state`/Selenium APIs. The directory has no explicit `__init__.py`; Python namespace-package behavior may permit imports from a repository-root checkout, but this must be verified in a clean environment. The current layout couples some provider and network concerns, so do not mechanically split classes into the proposed `providers/` and `networks/` folders until adapter boundaries and shared behavior are documented.

### Runtime/data-path findings

- Source mode currently derives runtime root as the repository root; frozen mode derives it from the executable directory.
- `core/state.py` owns `likepilot.db` and imports legacy `agents.json` and `stats.json`.
- `core/database.py` independently defaults to a database path relative to the current `core/` location, which is a different path policy from `core.state`.
- `core/backup_manager.py` also assumes `likepilot.db` is in the runtime root.
- `core/config.py` reads runtime-root `config.json`; `farm.py` loads runtime-root `.env`.
- `farm.py` writes `runtime_port.txt` under the runtime root.
- `dashboard_desktop.py` creates `logs/` and `diagnostics/` relative to the dashboard's current `PROJECT_ROOT`.
- The proposed `data/` relocation must therefore be implemented centrally and include compatibility/migration behavior; moving data files alone would break existing installations.

### Redundancy and launch-path conclusions (static review only)\n\n**Web-only direction (2026-11-05):** `farm.py` is the current browser-server launcher candidate. `likepilot_desktop.py` and `dashboard_desktop.py` are pywebview wrappers and are no longer target launch modes. The web-only install should not require pywebview. Confirm the server lifecycle, browser access, configuration, and data persistence before deleting legacy wrappers or packaging files.

1. `core.state` is the active primary persistence path used by the server, dashboard and runtime.
2. `core.database` has a distinct schema and a direct import from smart timing, but the current smart-timing data path is largely demonstrative. It remains separate until schema/call-site decisions are made.
3. `core.agents` is imported by `web/app.py`; its functions delegate to `core.state`. It is a compatibility facade, not safe to remove without updating imports.
4. `core.stats` has no tracked internal caller found by code search; it may still be an external compatibility surface.
5. `core.multiprocess_runtime.get_supervisor()` selects a supervisor based on config, but tracked launchers directly start `core.runtime.supervisor`. The multiprocessing setting therefore does not currently appear to control the primary launcher path.
6. `farm.py` is the health-checked server launcher (default port 5001). `likepilot_desktop.py` wraps that server and starts the threaded supervisor. `dashboard_desktop.py` starts the Flask app independently and appears to be a dashboard-only mode.
7. `start_silent.py` is Windows-specific despite being a Python file; its advertised port 5000 conflicts with the server default 5001.
8. `advanced_bot.py` appears to be an older standalone prototype and is not referenced by the tracked runtime; retain it until the intended legacy policy is approved.


### Individual dashboard asset paths

The dashboard groups above expand to these exact tracked paths and destinations:

| Current path | Proposed destination |
|---|---|
| `web/static/agents.js` | `src/likepilot/dashboard/static/agents.js` |
| `web/static/analytics.js` | `src/likepilot/dashboard/static/analytics.js` |
| `web/static/auth.css` | `src/likepilot/dashboard/static/auth.css` |
| `web/static/dashboard.css` | `src/likepilot/dashboard/static/dashboard.css` |
| `web/static/dashboard.js` | `src/likepilot/dashboard/static/dashboard.js` |
| `web/static/operations.js` | `src/likepilot/dashboard/static/operations.js` |
| `web/static/settings.js` | `src/likepilot/dashboard/static/settings.js` |
| `web/static/sw.js` | `src/likepilot/dashboard/static/sw.js` |
| `web/templates/analytics.html` | `src/likepilot/dashboard/templates/analytics.html` |
| `web/templates/dashboard.html` | `src/likepilot/dashboard/templates/dashboard.html` |
| `web/templates/index.html` | `src/likepilot/dashboard/templates/index.html` |
| `web/templates/layout.html` | `src/likepilot/dashboard/templates/layout.html` |
| `web/templates/login.html` | `src/likepilot/dashboard/templates/login.html` |
| `web/templates/operations.html` | `src/likepilot/dashboard/templates/operations.html` |
| `web/templates/settings.html` | `src/likepilot/dashboard/templates/settings.html` |
| `web/favicon/192x192.png` | `src/likepilot/dashboard/favicon/192x192.png` |
| `web/favicon/512x512.png` | `src/likepilot/dashboard/favicon/512x512.png` |
| `web/favicon/apple-touch-icon.png` | `src/likepilot/dashboard/favicon/apple-touch-icon.png` |
| `web/favicon/favicon-16x16.png` | `src/likepilot/dashboard/favicon/favicon-16x16.png` |
| `web/favicon/favicon-32x32.png` | `src/likepilot/dashboard/favicon/favicon-32x32.png` |
| `web/favicon/favicon.ico` | `src/likepilot/dashboard/favicon/favicon.ico` |
| `web/favicon/favicon.png` | `src/likepilot/dashboard/favicon/favicon.png` |
| `web/favicon/site.webmanifest` | `src/likepilot/dashboard/favicon/site.webmanifest` |

### Git history check for the missing integrations

A GitHub commit-history query for the path `modules/` returned no commits. This means the missing integration directory was not present in the repository's visible path history, rather than being removed in a later tracked commit. It does not rule out ignored or uncommitted local files. The local checkout must still be checked before deciding whether the implementation needs to be restored from another source or developed.


### Integration source update (2026-11-05)

The `modules/` directory is present on remote `main` with eight Python files. Static class-name reconciliation against `core/runtime.py` found no missing imported class definitions. This resolves the previous source-location blocker (A-001) but does not prove that Selenium/browser workflows execute correctly. Before moving these files, verify namespace-package imports, dependencies, browser setup, and provider/network action behavior from a clean checkout. The likely migration is coordinated under `src/likepilot/integrations/`; preserve current adapter coupling initially and refine the provider/network split only after tracing actual responsibilities.
\n\n### Web-only direction update (2026-11-05)\n\nThe product direction is now a browser-accessed web application, with a clone/configure/install/start workflow. The approved target tree contains no desktop package or executable packaging area. Desktop wrappers, desktop-specific launchers, and executable build assets are to be removed after reference and data-path checks. No application files have been removed or moved as part of this decision.\n