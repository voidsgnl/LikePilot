# LikePilot Roadmap

**Project status:** Working but incomplete; active development  
**Primary branch:** `main`  
**Roadmap policy:** This file is the shared progress tracker. Update task status and evidence as work is completed. Do not mark an item complete until its acceptance criteria have been verified.

LikePilot is a multi-platform automation and agent-management application. It connects engagement/task providers with social networks; Like4Like is one provider, not the product identity.

The project is intended for educational, experimental, and software-development use. Users remain responsible for complying with the terms and policies of each connected service and for automating only accounts and environments they are authorized to use.

## Status key

- [ ] Not started
- [~] In progress
- [x] Completed and verified
- [!] Blocked / requires a decision

## Development principles

- Preserve existing working behavior while improving the internals.
- Investigate before deleting, renaming, merging, or moving files.
- Resolve file redundancy when the relevant code paths are understood; avoid speculative cleanup.
- Keep changes on `main`; do not create feature branches unless explicitly requested.
- Prefer small, verifiable changes with tests or reproducible checks.
- Keep the roadmap current as implementation and audit findings evolve.
- Do not describe an integration or platform as supported until its code and execution path have been verified.

---

## Phase 0 — Repository and runtime integrity

**Goal:** Establish what is actually present, what starts, and which code paths are authoritative before restructuring.

- [~] **P0.1 — Resolve and verify integration package**
  - [x] Confirm the `modules/` source exists in the remote `main` tree.
  - [x] Trace the `core/runtime.py` imports and identify the required integration classes.
  - [ ] Verify clean-checkout imports and primary application startup.
  - [ ] Confirm runtime behavior for each registered provider/network/action combination.
  - **Acceptance:** A clean checkout can import and start the primary runtime; each registered integration has an identifiable implementation and a verified execution path.

- [ ] **P0.2 — Verify startup paths**
  - [ ] Trace `farm.py`, `likepilot_desktop.py`, `dashboard_desktop.py`, and `start_silent.py`.
  - [ ] Identify the intended primary launch path and supported alternate launch modes.
  - [ ] Check dashboard ports, startup health checks, shutdown behavior, and error reporting.
  - **Acceptance:** Each documented launch command starts the intended service or exits with a useful actionable error.

- [ ] **P0.3 — Dependency and import audit**
  - [ ] Compare imports across the project with declared dependencies.
  - [ ] Separate required runtime, desktop UI, development, and optional dependencies.
  - [ ] Verify dependency availability and compatibility on the intended Windows and Linux source workflows.
  - **Acceptance:** A clean environment can install the documented dependency set and pass import/startup checks for the selected mode.

- [ ] **P0.4 — Configuration and security baseline**
  - [ ] Resolve duplicate keys and placeholder values in `config.json`.
  - [ ] Replace insecure default dashboard credentials with a first-run setup or required environment configuration.
  - [ ] Verify secret handling, session signing, local network binding, and credential storage.
  - [ ] Review updater defaults and disable unsafe automatic installation until update validation is implemented.
  - **Acceptance:** No shipped default credential or placeholder configuration can be mistaken for a production-ready value; dashboard access is safely configured.

## Phase 1 — Directory structure and redundancy

**Goal:** Make the repository easier to navigate without breaking imports, packaging, runtime data, or user workflows.

- [x] **P1.1 — Inventory root-level files**
  - [ ] Classify every root file as entrypoint, configuration, documentation, packaging, development utility, runtime data, or legacy.
  - [x] Identify which root files must remain for standard Python entrypoints or release tooling.
  - **Acceptance:** Every root-level item has a documented purpose and a proposed destination or an explicit reason to remain.

- [x] **P1.2 — Design the target directory layout**
  - [ ] Propose a clean structure for application source, integrations, dashboard assets, configuration examples, scripts, tests, packaging, and documentation.
  - [ ] Keep runtime-generated data (logs, profiles, databases, backups, diagnostics) outside source-code directories.
  - [~] Define import/package conventions before moving files; the initial package/import strategy is recorded in [`docs/architecture/directory-migration-map.md`](docs/architecture/directory-migration-map.md).
  - [x] Complete the tracked file-by-file inventory and record verification gates for each proposed destination.
  - **Acceptance:** A reviewed migration map exists before any bulk file moves.

- [ ] **P1.3 — Identify and resolve redundant files**
  - [ ] Compare `core/state.py` and `core/database.py` responsibilities and callers.
  - [ ] Compare `core/agents.py` and agent operations in `core/state.py`.
  - [ ] Compare `core/stats.py` and statistics functions in `core/state.py`.
  - [ ] Compare `core/runtime.py` and `core/multiprocess_runtime.py` supervisor responsibilities.
  - [ ] Compare startup/server responsibilities in `farm.py`, `dashboard_desktop.py`, and `likepilot_desktop.py`.
  - [ ] Identify unused, obsolete, duplicate, and compatibility files through import and execution tracing.
  - **Acceptance:** Each consolidation or removal has verified callers, migration notes where needed, and regression checks.

- [ ] **P1.4 — Restructure incrementally**
  - [ ] Move files in small logical groups according to the approved migration map.
  - [ ] Update imports, entrypoints, resource paths, packaging configuration, and documentation with each move.
  - [ ] Remove obsolete files only after confirming no supported path depends on them.
  - **Acceptance:** The application imports and starts after each migration stage; no user data is moved or deleted unintentionally.

## Phase 2 — Core application and integration reliability

**Goal:** Make the existing product behavior predictable and auditable.

- [ ] **P2.1 — Integration inventory**
  - [ ] List each engagement/task provider: Like4Like, KingdomLikes, and YouLikeHits.
  - [ ] List each social-network integration: Facebook, Instagram, TikTok, X/Twitter, and YouTube.
  - [ ] Map provider + network + action combinations to actual implementation classes.
  - [ ] Record status per integration: working, partially working, blocked, planned, or unavailable.
  - **Acceptance:** The dashboard and documentation do not advertise unverified capabilities.

- [ ] **P2.2 — Agent lifecycle**
  - [ ] Verify create, configure, start, pause, resume, stop, restart, and delete flows.
  - [ ] Verify state persistence and recovery after application restart.
  - [ ] Verify worker failures, timeouts, retries, and graceful shutdown.
  - **Acceptance:** Agent state transitions are consistent and failures are visible in logs and UI.

- [ ] **P2.3 — Browser and task execution**
  - [ ] Verify browser creation, profile isolation, driver lifecycle, and cleanup.
  - [ ] Verify task parsing, execution outcomes, and credit/result validation.
  - [ ] Verify rate-limit handling, safe retry behavior, and configurable delays.
  - [ ] Test supported browser and operating-system combinations.
  - **Acceptance:** Supported workflows complete reliably and report actionable errors without silently claiming success.

- [ ] **P2.4 — Runtime and concurrency**
  - [ ] Determine whether threaded and multiprocessing supervisors are both needed.
  - [ ] Verify process start method, inter-process state consistency, locks, monitoring, and shutdown.
  - [ ] Remove or consolidate unused runtime implementations only after testing.
  - **Acceptance:** The selected execution model is documented and does not corrupt shared agent state.

## Phase 3 — Dashboard and user experience

- [ ] **P3.1 — Audit dashboard features against backend behavior.**
- [ ] **P3.2 — Ensure settings persist and are validated.**
- [ ] **P3.3 — Improve agent status, activity, analytics, and error visibility.**
- [ ] **P3.4 — Ensure desktop and browser dashboard modes have consistent behavior.**
- **Acceptance:** Visible controls map to implemented backend behavior, with clear loading, empty, success, and error states.

## Phase 4 — Data, privacy, and operational safety

- [ ] **P4.1 — Consolidate persistence responsibilities and document the schema.**
- [ ] **P4.2 — Verify database migrations, backups, restore, and corruption recovery.**
- [ ] **P4.3 — Review credential storage and protect sensitive configuration.**
- [ ] **P4.4 — Review logs and diagnostics for accidental secret exposure.**
- [ ] **P4.5 — Harden updater download, archive validation, path traversal protection, backup, rollback, and version comparison.**
- [ ] **P4.6 — Review dashboard authentication, session handling, and network exposure.**
- **Acceptance:** User data can be backed up and restored; secrets are not exposed in logs; update and dashboard behavior has documented safeguards.

## Phase 5 — Installation, portability, and packaging

**Goal:** Support both executable distribution and source-based development without conflating the two.

- [ ] **P5.1 — Define Windows executable packaging**
  - [ ] Identify the supported entrypoint and required bundled resources.
  - [ ] Build a reproducible executable from a clean environment.
  - [ ] Verify first-run data directories, WebView2 requirements, logs, and upgrade behavior.
  - **Acceptance:** A clean Windows machine can follow the release instructions and launch the packaged application.

- [ ] **P5.2 — Define source installation**
  - [ ] Document Python version constraints and virtual-environment setup.
  - [ ] Provide explicit install commands for core and optional desktop dependencies.
  - [ ] Verify launch from a clean source checkout.
  - **Acceptance:** A developer can clone the repository, install dependencies, configure the app, and run the documented source entrypoint.

- [ ] **P5.3 — Verify Linux source workflow**
  - [ ] Replace Windows-only launcher assumptions where a cross-platform equivalent is intended.
  - [ ] Verify browser driver, WebView, and system-library requirements.
  - [ ] Document any platform-specific limitations.
  - **Acceptance:** Linux support is stated only for workflows that have been tested successfully.

- [ ] **P5.4 — Release automation**
  - [ ] Add build and validation scripts.
  - [ ] Add automated checks for imports, tests, and packaging.
  - [ ] Define versioning, release assets, checksums, and release notes.
  - **Acceptance:** Release artifacts are reproducible and accompanied by installation and verification instructions.

## Phase 6 — Testing and quality gates

- [ ] **P6.1 — Establish a test layout and baseline test suite.**
- [ ] **P6.2 — Add unit tests for configuration, paths, state, and persistence.**
- [ ] **P6.3 — Add integration tests for startup, dashboard routes, and agent lifecycle.**
- [ ] **P6.4 — Add platform-specific smoke tests for supported install modes.**
- [ ] **P6.5 — Add linting, formatting, and dependency checks.**
- **Acceptance:** Changes to core modules have automated regression coverage and the documented checks pass on a clean checkout.

## Phase 7 — Documentation and project maturity

- [ ] **P7.1 — Replace the current Windows-only README with accurate multi-platform project documentation.**
- [ ] **P7.2 — Document provider vs. social-network integrations and verified feature status.**
- [ ] **P7.3 — Add source installation, executable installation, configuration, troubleshooting, and backup/restore guides.**
- [ ] **P7.4 — Document architecture and the final directory structure.**
- [ ] **P7.5 — Maintain changelog and release notes.**
- **Acceptance:** Documentation matches tested behavior and clearly distinguishes available, partial, planned, and unsupported features.

---

## Current audit register

| ID | Finding | Status | Resolution rule |
|---|---|---|---|
| A-001 | `core/runtime.py` imports the `modules/` integration package | [~] Source restored and statically mapped | Remote `main` now contains eight module files; runtime imports are present in the source. Verify clean-checkout import/startup and execution behavior before marking complete |
| A-002 | Root directory contains application entrypoints and other mixed-purpose files | [x] Inventory and mapping complete | Move only after package/import and runtime-path migration gates pass |
| A-003 | Persistence responsibilities overlap between `core/state.py` and `core/database.py` | [~] Traced partially | `core.state` is primary app state; `core.database` has a separate schema and is imported by smart timing. Keep separate until schema and actual usage are fully reconciled |
| A-004 | Agent and statistics wrapper modules overlap with `core/state.py` | [~] Traced partially | `core.agents` is imported by the dashboard and delegates to state; `core.stats` has no tracked internal caller found. Preserve both pending compatibility review |
| A-005 | Threaded and multiprocessing runtime implementations overlap | [~] Traced partially | Current launchers start the threaded supervisor directly; the multiprocessing selector has no tracked caller found. Verify intended mode before consolidation |
| A-006 | Multiple launchers overlap in server and desktop startup responsibilities | [~] Static trace complete | `farm.py` is the health-checked server; `likepilot_desktop.py` wraps it; `dashboard_desktop.py` starts a separate dashboard server. Verify intended modes and smoke tests before consolidating |
| A-007 | Desktop dependencies appear absent from the single requirements file | [ ] Open | Split and verify dependency groups |
| A-008 | Updater repository setting contains a placeholder owner/repository | [ ] Open | Configure only after update and release design is safe |
| A-009 | Dashboard has a default credential fallback | [ ] Open | Replace with secure first-run or environment-based configuration |
| A-010 | `config.json` has a duplicate `performance` key and example placeholder values | [ ] Open | Normalize configuration while preserving intended settings |
| A-011 | Silent launcher uses Windows-only process flags and reports a port inconsistent with the main launcher | [~] Confirmed by static review | Windows-only flags; launcher advertises 5000 while `farm.py` defaults to 5001. Correct during launcher redesign and verify on target OSes |

## Change tracking

Record significant changes here. Keep entries factual and include verification results.

| Date | Change | Verification |
|---|---|---|
| 2026-11-05 | Initial roadmap created from the repository audit. No application files changed as part of this roadmap creation. | Initial tracked-tree and source inspection; implementation work remains pending. |
| 2026-11-05 | Approved target directory direction and added the initial file-by-file migration map at `docs/architecture/directory-migration-map.md`. No application files moved or modified. | Static inspection of core, runtime, dashboard, launchers, configuration, and dependency declarations; full inventory and runtime verification remain pending. |
| 2026-11-05 | Completed the tracked-file inventory and static dependency/entrypoint trace; expanded the migration map with per-file destinations and data-path risks. No application files moved or modified. | Reviewed all 66 tracked paths, core modules, launchers, config/state ownership, and searched tracked code for missing integration classes and runtime selector callers. Clean-checkout import and startup verification remains pending; the integration source was subsequently added to remote `main`. |
| 2026-11-05 | Checked Git history for the then-missing `modules/` path and expanded the migration map with exact dashboard asset paths. | GitHub path-history query returned no commits for `modules/` at that time; the integration source was later committed to `main`. |
| 2026-11-05 | Completed the tracked-file inventory and static dependency/entrypoint trace; expanded the migration map with per-file destinations and data-path risks. No application files moved or modified. | Reviewed the original tracked tree, core modules, launchers, config/state ownership, and runtime selector callers. Integration source was subsequently added; startup verification remains open. |

## Decision log

| Date | Decision | Reason |
|---|---|---|
| 2026-11-05 | Keep `main` as the working branch; do not create feature branches. | Project workflow preference. |
| 2026-11-05 | Investigate redundancy before deleting or merging files. | Similar names do not prove equivalent behavior or safe removal. |
| 2026-11-05 | Treat executable distribution and source installation as separate supported workflows. | They have different dependencies, launch paths, and packaging requirements. |
| 2026-11-05 | Describe LikePilot as multi-platform, with providers distinct from social networks. | Like4Like is one provider, not the product identity. |
| 2026-11-05 | Use the approved `src/likepilot` package layout with separate integrations, dashboard, desktop/entrypoints, scripts, packaging, tests, docs, and runtime data areas as the target architecture. | Reduce root clutter while preserving distinct runtime responsibilities; validate import and data-path changes before migration. |

| 2026-11-05 | Verified the remote `modules/` directory and reconciled it with `core/runtime.py`; updated A-001 and P0.1. No application files moved or modified. | Eight module files present; all runtime-imported class names are defined in the integration source. Static verification only; clean-checkout import, startup, and live execution remain untested. |
