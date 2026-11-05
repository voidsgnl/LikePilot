# Directory Migration Map

**Status:** Draft mapping for the approved target architecture  
**Branch:** `main`  
**Rule:** This document is an inventory and migration plan, not authorization to move or delete files without the verification gates below.

## Target layout

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

The `src/likepilot` layout requires a deliberate package/import migration. Existing imports such as `from core...` and `from web...` must not be broken by moving files. We will either convert imports consistently to the package namespace and configure packaging, or retain temporary compatibility entrypoints during migration.

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

- `modules/` is imported by `core/runtime.py` but is absent from the tracked `main` tree. Do not create placeholder bot classes or relocate imagined files. Locate the real source first.
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

- `core/runtime.py` imports classes from an untracked `modules/` package. This is a blocker to validating the package move.
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
