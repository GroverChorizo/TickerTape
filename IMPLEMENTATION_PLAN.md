# Implementation Plan

Last updated: 2026-03-23

This plan enumerates the work required to realize the MVP of the TickerTape terminal application. It is derived from the PRD and the specifications in the `specs/` directory, then reconciled with the current codebase. Tasks are organized by Epic -> Story -> Task. Each task includes acceptance criteria, estimated complexity, likely files, and a status.

## Current State Snapshot

- The app shell and profile screens exist, and much of the backend/TUI surface area has been scaffolded.
- Core constraints from PRD/Vision remain valid: local-first, deterministic, no synthetic production data, no financial advice.
- Runtime stability baseline has been restored for current test coverage.
- Verification run on 2026-03-23:
  - `python -m pytest -q` (algo env) -> `180 passed`.
  - `python -m ruff check .` (algo env) -> pass.
  - `python -m mypy .` (algo env) -> pass.
  - User-reported Day Trader `Signals` tab crash (`NotRenderableError`) is fixed with regression tests.
  - `python tools/data_integrity_gate.py --root .` -> PASS.
  - Determinism/provenance guardrails added: golden checksum tests + dedicated CI workflow (`.github/workflows/backtest.yml`).

## Gap Analysis Summary (by spec)

- Stability & Reliability: **Improved.** Known runtime crash and test-suite contract breaks fixed (TT-104/105/106/108).
- Command System: **Partial.** Core commands exist, but full Vision behavior (history/fuzzy/context and conflict handling parity) needs re-validation.
- UI Layout: **Partial.** Breakpoints exist; status/alert affordances still below full Vision spec.
- Profiles: **Partial.** Screens exist; broader feature parity with Vision remains incomplete.
- Data Ingestion: **Partial.** Adapter parity and stream telemetry improved; full endpoint/fallback parity still needs completion.
- Data Validation: **Mostly done.** Core validators exist; production-path validation coverage for new feeds remains thin.
- Backtesting & Resampling: **Done at MVP scope.** Engine, runner, provenance storage, schema migration checks, and determinism CI are in place.
- Secrets/Privacy: **Mostly done.** Guardrails exist and integrity gate passes; final audit checklist still needed.
- Alerts & Notifications: **Partial.** Triggering exists, but alert panel/sidebar and UX parity are incomplete.
- Architecture & Quality: **Partial.** Feature velocity outpaced contract discipline; missing integration tests allowed regressions.

**Immediate priority shift (Recovery Mode):** stabilize rendering/contracts first, then close Vision parity gaps with strict test gates.

## Vision Coverage Checklist

This checklist traces the authoritative Vision docs (`BtheVision_v1_5_5.txt`, `docs/FtheVision_v1_5_5.txt`) to plan coverage.

- Workflow + profile intent (DayTrader, LiquidationHunter, WhaleWatcher, FundingArbitrageur): covered by TT-030..TT-033 and TT-109.
- Endpoint-driven data model (ticks, orderbook, positions, liquidations, whales, smart-money, HLP): covered by TT-010..TT-012, TT-094, TT-109, TT-110.
- Hybrid interaction model + command palette + keybindings: covered by TT-060..TT-062 and TT-116.
- Responsive layout + density/fullscreen + profile-specific screens: covered by TT-050..TT-056 and TT-108/TT-113.
- Startup wizard + settings + panel customization: covered by TT-070..TT-071 and TT-055.
- Alert semantics (whales, cascades, funding extremes, anomalies): covered by TT-090..TT-091, TT-097, TT-111, TT-114.
- Status indicators (connection/API/WS/freshness/bandwidth/alerts): covered by TT-113.
- MVP visualization matrix (sparklines, orderbook bars, heatmaps, flow bars, liquidation distance): covered by TT-100..TT-101 and TT-115.
- Research/backtesting workstation (engine, MC, walk-forward, runner, provenance): covered by TT-040..TT-043, TT-095..TT-096, TT-099, TT-112.
- Governance constraints (local-first, no synthetic production data, no financial advice/live execution defaults): enforced via PRD + AGENTS + TT-117..TT-118.

## Epics and Stories

### Epic 1 - Project Setup & Scaffolding

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-001 | Repository scaffolding | 1. Initialize `profiles/`, `providers/`, `validators/`, `backtesting/`, `ui/`, `commands/` packages with `__init__.py` files. 2. Create base classes: `Profile` (in `profiles/base.py`), `Provider` (in `providers/base.py`), `Validator` (in `validators/base.py`), `Panel` (in `ui/panel.py`), and `Command` registry. | All packages exist with base classes defined; the app can import these without errors. | New files; updates to `setup.py` or `pyproject.toml` if needed. | S | Done - base packages and base classes added at repo root. |
| TT-002 | Build test harness | 1. Configure pytest with a `tests/` directory. 2. Add example test for a dummy validator. 3. Ensure `pytest` runs successfully. | `pytest` collects and runs dummy tests without failure. | `tests/conftest.py`, `tests/test_dummy.py` | S | Done - pytest configured, multiple tests present. |
| TT-003 | Secrets file management | 1. Define a configuration specification for a secrets file. By default, look for `~/.ticker_tape/secrets.yaml` (or `.secrets`) but allow the path to be overridden via env var or CLI arg. 2. Modify startup sequence and wizard to create this file if it does not exist and inform the user. 3. Provide a CLI command `:secrets` to print the secrets file path and open it in an editor. | Running the app without specifying a secrets path creates the default secrets file and logs its path. The command `:secrets` prints the path and opens the file. Unit tests verify creation and reading. | `src/config/secrets.py`, `tui/wizard.py`, `tui/app.py`, `tests/config/test_secrets.py` | M | Done - YAML secrets module, CLI command, wizard integration, and tests added. |
| TT-004 | CLI entry points | 1. Configure build system to expose console scripts named `TickerTape` and `TTape` that run the application’s main entry point. 2. Update docs to document new commands. | After installation, running `TickerTape` or `TTape` launches the application. A test running these commands via subprocess succeeds. | `setup.py`, `README.md`, `AGENTS.md`, `tests/test_cli_entrypoints.py` | S | Done - setup.py entry points added with tests and docs updates. |
| TT-005 | Playbooks | 1. Add missing playbooks for backend, frontend, research review, and privacy/security. 2. Reference playbooks in `AGENTS.md` and `README.md`. | `playbooks/` exists with four required playbooks; references updated. | `playbooks/*.md`, `AGENTS.md`, `README.md` | S | Done - playbooks added and referenced. |
| TT-006 | PRD alignment | 1. Move PRD to root `PRD.md` as canonical source. 2. Remove duplicate doc copy and align data integrity allowlist. | `PRD.md` is canonical; references align; integrity gate allowlist updated. | `PRD.md`, `.data_integrity_gate.json` | S | Done - PRD relocated and allowlist updated. |

### Epic 2 - Data Provider Layer

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-010 | Provider abstraction | 1. Define `Provider` interface in `providers/base.py` with methods for ticks, order book, liquidations, whale trades, funding rates and positions. 2. Create typed data models (`Tick`, `OrderBookLevel`, `LiquidationEvent`, `WhaleTrade`, `FundingRate`, `Position`) in `providers/models.py`. | Interface methods and models are defined with type hints; unit tests import them without errors. | `providers/base.py`, `providers/models.py`, `tests/test_provider_models.py` | M | Done - provider models added with tests; base interface updated. |
| TT-011 | Hyperliquid provider | 1. Implement `HyperliquidProvider` adhering to the base interface. 2. Use HTTP/WS endpoints from the Hyperliquid Data Layer API with timeouts, retries and backoff. 3. Cache snapshots in memory; return typed models. | Provider returns correct data for at least one endpoint; snapshot caching works in unit tests. | `providers/hyperliquid.py`, `tests/test_provider_hyperliquid.py` | L | Done - HTTP snapshot implemented for liquidations with in-memory cache; WS support tracked in follow-up. |
| TT-012 | Provider diagnostics | 1. Implement a diagnostic helper that checks connectivity and returns a summary (HTTP latency, WS state, last update). 2. Expose a command `:diagnose provider`. | Running the command prints a report with latency values; unit test covers typical case. | `providers/diagnostics.py`, `commands/diagnose.py`, `tests/test_provider_diagnostics.py` | S | Done - diagnostics helper + command formatter + tests added. |

### Epic 3 - Data Validation

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-020 | Validator framework | 1. Create abstract `Validator` base class in `validators/base.py` with a `validate()` method returning a `ValidationReport`. 2. Define `ValidationReport` dataclass with error/warning counts and details. 3. Register validators via a registry. | Base class and registry work; unit tests can register and run a dummy validator. | `validators/base.py`, `validators/registry.py`, `validators/report.py`, `tests/validators/test_registry.py` | M | Done - added report + registry + tests; base validate returns ValidationReport. |
| TT-021 | Core validators | Implement built-in validators: Schema, Missingness, Range, Monotonic, Duplicate, Outlier. Add unit tests using fixture data. | Each validator correctly identifies violations; tests cover success and failure cases. | `validators/schema.py`, `validators/missingness.py`, etc.; `tests/validators/test_*` | L | Done - core validators implemented with unit tests. |
| TT-022 | Validation command | 1. Add a CLI command `:validate <dataset>` that runs all validators on the specified snapshot and displays a summary table. 2. Implement UI integration in a modal window. | Running the command on a fixture dataset prints a validation summary; unit test verifies output. | `tui/validation.py`, `tui/ui/screens/validation.py`, `tui/app.py`, `tests/commands/test_validate.py` | M | Done - command + validation screen + tests added. |

### Epic 4 - Profile Modules

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-030 | Day Trader profile | 1. Create `profiles/day_trader.py` implementing the profile interface. 2. Register four panels (Price Chart, Top Positions, Whale Flow, Liquidation Stats). 3. Add watchlist management and anomaly detection. | Day Trader screen loads with four panels and updates from live data; watchlist command works in tests. | `tui/ui/screens/profile_day_trader.py`, `tui/app.py`, `tests/profiles/test_day_trader.py`, `tests/commands/test_watchlist.py` | L | Done - Day Trader screen wired with watchlist command and panel sections (positions proxy). |
| TT-031 | Liquidation Hunter profile | 1. Implement `profiles/liquidation_hunter.py` with panels: Liquidation Heatmap, Liquidation Distance, Cascade Monitor. 2. Implement cascade detection helper and thresholds. | Screen displays heatmap and progress bars; cascade alerts trigger correctly in tests. | `tui/ui/screens/profile_liquidation.py`, `tui/widgets/liquidations_*`, `tests/test_liquidation_hunter.py` | L | Done - added heatmap, distance (positions snapshot if available), and cascade monitor sections with tests. |
| TT-032 | Whale Watcher profile | 1. Implement `profiles/whale_watcher.py` with panels: Whale Trade List, Directional Flow Bars, Whale Heatmap. 2. Add wallet inspection functionality. 3. Implement search filters for size and side. | Screen updates with real-time trades; selecting a wallet opens the wallet panel; tests cover UI and data. | `tui/ui/screens/profile_whale_watcher.py`, `tui/ui/screens/wallet_detail.py`, `tui/app.py`, `tests/profiles/test_whale_watcher.py` | L | Done - Whale Watcher screen with filters + wallet detail screen + tests. |
| TT-033 | Funding Arbitrageur profile | 1. Create `profiles/funding_arbitrageur.py` with panels: Funding Heatmap, Funding Extremes, Arbitrage Comparison. 2. Implement arbitrage detection logic with thresholds. 3. Provide commands to add/remove exchanges. | Screen shows heatmap and comparison table; arbitrage alerts fire on test data; tests ensure detection logic is correct. | `tui/ui/screens/profile_funding_arbitrage.py`, `tui/app.py`, `tests/profiles/test_funding_arbitrage.py` | L | Done - Funding Arbitrage screen uses multi-exchange feed, heatmap/extremes/arbitrage sections, tests added. |

### Epic 5 - Backtesting and Simulation Engine

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-040 | Backtest engine | 1. Implement core engine that runs strategies over historical data with no lookahead bias. 2. Compute equity curve, trades, P&L and risk metrics. 3. Return a `BacktestResult` object. | Engine processes a sample strategy and produces correct metrics; tests compare with expected values. | `backtesting/engine.py`, `backtesting/models.py`, `tests/backtesting/test_engine.py` | L | Done - deterministic engine with metrics + tests added. |
| TT-041 | Monte Carlo simulation | 1. Implement Monte Carlo runner that bootstraps returns and produces a set of equity trajectories. 2. Output fan chart data and summary stats. | Running Monte Carlo on a fixture dataset produces expected percentiles; tests verify reproducibility. | `backtesting/monte_carlo.py`, `tests/backtesting/test_monte_carlo.py` | M | Done - deterministic resampling engine + tests added. |
| TT-042 | Walk-forward testing | 1. Implement walk-forward module that splits data into train/test windows and executes strategies. 2. Compute average train/test metrics and degradation. | Module returns a report summarizing OOS Sharpe and degradation; tests validate outputs on fixture data. | `backtesting/walk_forward.py`, `tests/backtesting/test_walk_forward.py` | M | Done - walk-forward report implemented with tests. |
| TT-043 | Strategy integration | 1. Add ability for users to load custom strategy modules from a file path. 2. Validate that strategies implement the required interface. | Loading an example strategy file triggers correct backtest results; tests cover invalid strategies. | `commands/backtest.py`, `backtesting/loader.py`, `tests/backtesting/test_loader.py` | M | Done - subprocess runner with explicit confirmation + tests. |
| TT-044 | Backtest UI | 1. Implement a backtest panel that displays equity curves and drawdowns using sparklines or area charts. 2. Integrate with command system (`:backtest`). | Running a backtest via command opens a panel with results; tests include UI assertions. | `ui/panels/backtest.py`, `commands/backtest.py`, `tests/ui/test_backtest_panel.py` | L | Not started |

### Epic 6 - User Interface and Layout

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-050 | Layout manager | 1. Implement responsive layout logic with breakpoints for ultra-wide, wide, standard, narrow and compact modes. 2. Support separate screens per profile and switching between them. | Changing terminal width triggers correct layout adjustments in tests; switching profiles changes the entire view. | `tui/ui/layout.py`, `tui/ui/screens/base.py`, `tui/tui.css`, `tests/ui/test_layout.py` | L | Done - layout breakpoint classes with resize handling and tests. |
| TT-051 | Panel framework | 1. Create a Panel base class with states (focused, alert) and built-in animations. 2. Implement common panel widgets (tables, heatmaps, bar charts, sparkline charts). | Panels render correctly in isolation; tests cover focus transitions and alert flashing. | `tui/widgets/panel_base.py`, `tui/widgets/charts.py`, `tests/ui/test_panel_framework.py` | L | Done - alert state + chart widgets + tests. |
| TT-052 | Theming and styles | 1. Define CSS styles for each theme (cypherpunk, Dark Pro, Matrix, Minimal). 2. Implement accent colors and spacing system. 3. Provide commands to switch themes (`:theme cypherpunk`). | Switching themes updates colors across the UI; tests verify style variables. | `tui/themes/*`, `tui/tui.css`, `commands/theme.py`, `tests/ui/test_theme.py` | M | Done - theme command added, theme CSS tokens/spacings defined, tests cover CSS tokens. |
| TT-053 | Sidebar and tabs | 1. Implement responsive sidebar with icon-only mode; create bottom tab bar for narrow screens. | Sidebar collapses appropriately; tests verify tab switching. | `tui/ui/sidebar.py`, `tui/ui/tabbar.py`, `tests/ui/test_sidebar.py` | M | Done - sidebar + tabbar widgets, BaseScreen wiring, CSS updates, tests added. |
| TT-054 | Fullscreen and density | 1. Add fullscreen toggle for panels (F key) and density mode toggle (D key). 2. Persist user choice per session. | Pressing F and D toggles states correctly; tests cover persistence. | `tui/ui/fullscreen.py`, `tui/ui/density.py`, `tests/ui/test_fullscreen_density.py` | S | Done - toggles wired in BaseScreen with session persistence and CSS classes. |
| TT-055 | Panel resizing and custom dashboards | 1. Enhance panel framework to support drag-resize handles. 2. Implement dashboard customization workflow and persistence. 3. Load custom dashboards on start. | Panels can be resized; new custom profiles can be created, saved and loaded; tests verify persisted layout. | `tui/ui/layout.py`, `tui/ui/custom_dashboard.py`, `tests/ui/test_custom_dashboard.py` | L | Done - resizable panel helper, custom dashboard persistence + commands, startup load, tests added. |
| TT-056 | Tab carousel and breadcrumb navigation | 1. Implement navigation component listing open screens with keyboard shortcuts. 2. Show breadcrumb trail. 3. Persist open window order. | Users can cycle screens; breadcrumb shows position; tests cover persistence. | `tui/ui/tab_carousel.py`, `tui/ui/status_bar.py`, `tests/ui/test_tab_carousel.py` | M | Done - tab carousel + status bar, breadcrumb text, open screen order persistence, tests added. |

### Epic 7 - Command System

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-060 | Command parser and registry | 1. Implement command registry and parser to handle command definitions with arguments/options. 2. Provide error feedback for invalid commands. | Parser can register commands and parse sample strings; tests cover error conditions. | `commands/parser.py`, `commands/registry.py`, `tests/commands/test_parser.py` | M | Done - added parser + registry helpers and tests. |
| TT-061 | Command palette UI | 1. Implement CommandPalette widget with suggestions, history and syntax hints. 2. Integrate palette invocation (`/` or `Ctrl+K`). | Opening the palette displays suggestions; fuzzy search works; tests simulate user input. | `tui/ui/widgets/command_palette.py`, `tests/ui/test_command_palette.py` | L | Done - palette widget + modal screen, history/suggestions, Ctrl+K/`/` bindings, tests added. |
| TT-062 | Built-in commands | Implement global, navigation, data, backtest/MC, export, debug commands per spec. | Running each command performs its expected action; tests cover success and failure scenarios. | `tui/core/commands.py`, `tui/app.py`, `tests/commands/test_commands.py` | L | Done - added lifecycle/nav/data/export/debug commands with tests. |

### Epic 8 - Startup Wizard and Settings

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-070 | Wizard flow | 1. Implement multi-step wizard with screens: Welcome, Profile Selection, Theme Selection, Dashboard Customization, Alerts Configuration, Completion. 2. Persist selections to a config file. | Running the wizard from a fresh install guides the user through all steps; selections are stored and loaded on next launch. | `tui/wizard.py`, `tui/config.py`, `src/config/__init__.py`, `tests/test_tui_config.py`, `tests/test_tui_bootstrap.py` | L | Done - wizard now includes six steps with panel/alert selection and persists to config/session; config package import stabilized. |
| TT-071 | Settings panel | 1. Implement a Settings screen accessible via `Ctrl+,` that allows users to change profile, theme, panels and alerts. 2. Save changes to config and update UI accordingly. | Changing settings updates the application without restart; tests confirm persistence. | `tui/ui/screens/settings.py`, `tests/ui/test_settings.py` | M | Done - added settings screen, persistence helper, and tests. |

### Epic 9 - Multi-Exchange Funding Panel

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-080 | Multi-exchange panel | 1. Implement panel that displays funding rates across exchanges with computed spread and arbitrage flag. 2. Implement arbitrage detection logic using thresholds. 3. Provide commands to add/remove exchanges and refresh data. | Panel renders correctly with sample data; detection logic flags opportunities; tests verify. | `tui/feeds/funding.py`, `tui/widgets/funding_panel.py`, `tui/app.py`, `tests/panels/test_multi_exchange.py` | M | Done - arbitrage detection + spread column added; exchange commands + refresh added; tests updated. |

### Epic 10 - Alerts and Notifications

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-090 | Alert framework | 1. Implement global alert service that can queue and dispatch alerts with severity levels. 2. Define alert configuration (enabled events, thresholds) and persistence. | Alerts triggered by other modules display pop-ups with correct color coding; user can mute or clear alerts. | `src/backend/alerts.py`, `tui/state/alerts.py`, `tui/widgets/alert_panel.py` | M | Partial - alert store + popups + mute/clear exist; alert panel wiring pending. |
| TT-091 | Panel integration | Integrate alert triggers in panels: cascade alerts, whale trade alerts, funding extreme alerts and anomaly alerts. | When events exceed thresholds, the corresponding alert appears; tests simulate events. | `tui/ui/screens/*`, `tests/alerts/test_integration.py` | L | Partial - triggers wired in profile screens; missing tests + alert panel integration. |

### Epic 11 - Architecture Alignment

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-092 | Align spec paths with code structure | 1. Decide whether to migrate to top-level `profiles/`, `providers/`, `ui/`, `commands/` packages or keep the `tui/`-centric layout. 2. Update specs and import paths accordingly. | Specs and code paths agree; new contributors can follow a single structure without guesswork. | `IMPLEMENTATION_PLAN.md`, `specs/*`, `providers/*`, `commands/*` | S | Done - keep `tui/` as runtime core with top-level facades; specs updated to match. |
| TT-093 | Linting & typing hardening | 1. Revisit `ruff.toml` and `mypy.ini` to reduce global ignores. 2. Fix outstanding lint/type errors incrementally and align with repo style. | Ruff and mypy run with minimal ignores; remaining suppressions are localized with comments or per-module config. | `ruff.toml`, `mypy.ini`, offending modules | M | Done - removed global F401/E702 ignores, cleaned unused imports, and updated mypy exclusions for locked temp dirs. |
| TT-103 | Feed API: typed status & contract | 1. Introduce `FeedStatus` enum and use in `FeedResult` (frozen). 2. Make `fetch()` return `None` when no new data and document the contract. 3. Return immutable copies from `latest()` and add compatibility shim for string statuses. 4. Use status-aware logging (DEBUG for OK, WARNING otherwise) and update tests. | FeedResult is immutable with typed status; fetch contract documented and enforced; tests updated to use None for no-new-data fixtures; logging reflects status. | `tui/feeds/base.py`, `tests/test_tui_feeds.py`, `tests/test_tui_panel_states.py` | S | Done - FeedStatus + frozen FeedResult; fetch contract enforced; tests updated. |
| TT-094 | Provider streaming & additional endpoints | 1. Add WebSocket streaming support to the Hyperliquid provider with reconnect/backoff. 2. Implement at least one additional endpoint (orderbook or funding) returning typed models. 3. Add tests for WS reconnect and new endpoint parsing. | WS reconnect behavior validated in tests; new endpoint returns typed models; provider remains deterministic. | `providers/hyperliquid.py`, `providers/ws.py`, `tests/test_provider_hyperliquid.py` | M | Partial - streaming methods + orderbook parsing added; WS harness tests pending. |

---

### Epic 12 - Research Jobs & Provenance 🔧

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-095 | Provenance & job store | 1. Define a `BacktestJob` metadata model capturing: strategy name/version, dataset(s), timeframe(s), parameters, random seed(s), start/end timestamps and result path. 2. Implement a local job store under `~/.ticker_tape/jobs/<run_id>/` that writes metadata and serialized `BacktestResult` in JSON/Parquet. 3. Add CLI commands `:jobs list` and `:jobs show <id>`. | Running a backtest writes a run folder with metadata and result files; `:jobs list` shows recent runs and `:jobs show` prints detailed metadata. Unit tests cover metadata serialization and file layout. | `backtesting/job.py`, `commands/jobs.py`, `tests/backtesting/test_jobs.py` | M | Done - job store + CLI commands implemented. |

| TT-096 | Provenance tests & CI | 1. Add unit tests that assert deterministic `BacktestResult` given fixed seed and dataset fixture. 2. Include a lightweight end‑to‑end CI job that runs a sample backtest and compares output checksums to stored golden results. | Tests fail if backtest outputs change; CI job runs in <2 minutes and fails on non‑deterministic output. | `tests/backtesting/test_provenance.py`, `.github/workflows/backtest.yml` | M | Done - added deterministic golden checksum tests and dedicated `backtest.yml` CI gate. |

---

### Epic 13 - Alerts Completion 🔔

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-097 | Alert UI integration & per‑panel triggers | 1. Add alert configuration for panels (enabled events, thresholds, severity). 2. Wire `src/backend/AlertManager` events to panel-level triggers (cascade, whale, funding). 3. Implement mute/clear UX and a `:alerts` command to list recent alerts. | Simulated events generate UI pop-ups and entries in the alert panel; user can mute/clear alerts and `:alerts` lists recent items. Unit and UI tests exercise the flow. | `src/backend/alerts.py`, `tui/state/alerts.py`, `tui/ui/screens/*`, `tui/widgets/alert_panel.py` | L | Partial - alert store + mute/clear + triggers wired; alert panel and tests pending. |

---

### Epic 14 - Provider Streaming & Test Harness 🛰️

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-098 | Hyperliquid WS streaming & harness | 1. Add an asyncio WebSocket client to `providers/hyperliquid.py` with automatic reconnect/backoff and jitter. 2. Implement streaming handlers for at least orderbook and funding endpoints and ensure typed model emission. 3. Add a local test harness that replays recorded WS frames for deterministic testing. | WS reconnect/backoff behavior validated in unit tests; harness can replay recorded frames to verify parsing and backpressure handling. | `providers/hyperliquid.py`, `providers/ws.py`, `tests/test_provider_hyperliquid_ws.py` | M | Partial - streaming generators exist; harness/tests pending. |

---

### Epic 15 - Backtesting Minimal Runner & UI Integration 🎲

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-099 | Minimal backtest runner & TUI command | 1. Implement a lightweight backtest runner capable of executing a simple strategy script against historical snapshots (`backtesting/runner.py`). 2. Add a `:backtest run <file>` command that executes the runner, stores provenance (TT‑095) and writes a `BacktestResult`. 3. Add a simple result panel to display equity curve and summary metrics. | Running `:backtest run example_strategy.py` completes within 10s for fixture data, writes provenance and result files, and opens a result panel. | `backtesting/runner.py`, `commands/backtest.py`, `ui/panels/backtest.py`, `tests/backtesting/test_runner.py` | L | Done - Minimal runner, command and panel added; tests included. |

---

### Epic 16 - Tables & Data Visualization (Phase 1) 🧾

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-100 | Table styling & heat rows (Funding panel) | 1. Add numeric sign colorization (green/red) for rate, spread and annualized columns. 2. Add a compact heat indicator for `annualized_pct` showing relative magnitude. 3. Unit test verifying styled output for positive and negative values. | Funding panel table shows colored numbers and a heat indicator; unit test verifies presence of formatted values and ARB label. | `tui/widgets/funding_panel.py`, `tui/render/palette.py`, `tests/widgets/test_funding_table_style.py` | S | Done - initial styling and heat indicator added; more panels to follow. |

| TT-101 | Shared TableWidget & apply to other panels | 1. Enhance `TableWidget` to support numeric formatting and heat indicators. 2. Add unit tests for `TableWidget`. 3. Plan follow-up to replace per-panel formatting with shared widget. | `TableWidget` supports numeric_cols and heat_cols; tests verify numeric formatting and presence of heat bars. | `tui/widgets/charts.py`, `tests/widgets/test_table_widget.py` | S | Done - shared TableWidget enhanced and tests added; follow-ups planned. |
| TT-102 | Jobs CLI & UI | 1. Add `:jobs list` and `:jobs show <id>` commands; 2. Add a minimal Jobs screen. | `:jobs list` runs and `:jobs show <id>` shows run metadata; unit tests included. | `commands/jobs.py`, `tui/ui/screens/jobs.py`, `tests/commands/test_jobs.py` | S | Done - CLI commands and tests added (UI screen stub added). |

---

### Epic 17 - Stabilization & Contract Recovery 🚑

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-104 | Fix render contract for mixed Rich/Text lines | 1. Normalize tuple-based lines to Rich `Text` before passing to `Group`. 2. Patch `RawJsonPanel` and any similar render paths. 3. Add regression test that mounts Day Trader screen and opens `Signals` tab. | Clicking `Signals` no longer raises `NotRenderableError`; regression test fails before fix and passes after fix. | `tui/widgets/raw_json_panel.py`, `tests/widgets/test_raw_json_panel.py` | S | Done - tuple renderable converted to Text before Group; regression tests added. |
| TT-105 | Restore streaming supervisor contract | 1. Reconcile `tui.streaming` API with tests (`StreamSupervisor` vs `LiveStreamManager`). 2. Either reintroduce compatibility shim or migrate tests/callers. 3. Document canonical streaming entrypoint. | `pytest -q` collects all tests without import errors; streaming architecture is explicit in docs. | `tui/streaming.py`, `tests/test_stream_supervisor.py`, `tests/test_stream_manager.py` | S | Done - compatibility `StreamSupervisor` restored while keeping `LiveStreamManager`. |
| TT-106 | Unify endpoint allowlists across backend and TUI | 1. Consolidate endpoint keys used by `src/backend/network.py` and `tui/feeds/url_builder.py`. 2. Remove stale aliases or add explicit compatibility mapping. 3. Update tests accordingly. | `tests/test_network.py` passes; no endpoint-key mismatch between backend and TUI layers. | `src/backend/network.py`, `tests/test_network.py`, `tests/test_url_builder.py` | M | Done - backend allowlist updated to include Vision-aligned keys used by tests/runtime. |
| TT-107 | De-flake async timing tests | 1. Replace brittle wall-clock assertions with tolerance or monotonic deadline checks. 2. Add deterministic async test helper. | Timing tests pass consistently on Windows and CI without false failures. | `tests/test_profile_liquidation_nonblocking.py` | S | Done - replaced strict wall-clock bound with tolerance-based helper assertion. |
| TT-108 | Add tab-switch smoke suite for all profiles | 1. Add UI smoke tests that open each profile and switch every `TabbedContent` tab. 2. Assert no unhandled exceptions and panel renderables are valid Rich objects. | A dedicated smoke suite catches render-time crashes like the `Signals` tab bug before merge. | `tests/ui/test_profile_tab_switch_smoke.py`, `tests/widgets/test_raw_json_panel.py` | M | Done - smoke coverage added for Day Trader, Liquidation Hunter, Whale Watcher, and Funding Arbitrage tabs. |

---

### Epic 18 - Vision Parity: Backend/Data ⚙️

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-109 | Profile feed coverage against Vision endpoint map | 1. Map each profile panel to explicit required endpoint(s) from `BtheVision_v1_5_5.txt`. 2. Add missing feed adapters and contract tests for DayTrader/Liquidation/Whale/Funding profiles. | Each visible panel has a verified feed contract with fixture-based tests and clear fallback behavior. | `tui/feeds/contracts.py`, `tui/feeds/*.py`, `tui/providers/hyperliquid.py`, `tests/feeds/*`, `tests/profiles/*` | M | Partial - added profile contract map, endpoint allowlist checks, adapter kwarg parity tests, and provider typed-conversion tests; remaining gap is explicit fallback-path tests per profile panel. |
| TT-110 | WS resilience + health instrumentation | 1. Finish WS reconnect/backoff/jitter harness with replay fixtures. 2. Track active streams, lag, and reconnect counts in a structured status model. | WS tests validate reconnect behavior and health metrics; degraded/offline states are deterministic. | `providers/hyperliquid.py`, `providers/ws.py`, `tui/streaming.py`, `tests/test_provider_hyperliquid_ws.py` | M | Partial - added structured supervisor stats, streamer telemetry, manager metrics, and tests; remaining work is exposing telemetry in UI diagnostics/status surfaces. |
| TT-111 | Watchlist anomaly engine parity | 1. Implement anomaly checks for price/volume/funding/OI consistent with Vision thresholds. 2. Add per-symbol threshold config and tests. | Watchlist anomalies use deterministic threshold logic and trigger structured alerts in tests. | `tui/ui/screens/profile_day_trader.py`, `tests/profiles/test_day_trader.py` | M | Done - implemented price/volume/funding/OI anomaly checks with per-symbol threshold overrides and deterministic alert tests. |
| TT-112 | Determinism/provenance CI completion | 1. Complete TT-096 with golden-result checksums. 2. Wire CI gate for backtest determinism and provenance schema compatibility. | Determinism regressions fail CI; provenance schema changes require explicit migration updates. | `tests/backtesting/test_provenance.py`, `.github/workflows/backtest.yml`, `backtesting/job.py` | M | Done - schema-tagged provenance writes/reads + migration checks, deterministic timestamp injection, golden checksums, and CI workflow gate. |

---

### Epic 19 - Vision Parity: Frontend/TUI 🎛️

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-113 | Status bar parity with Vision | 1. Implement status components: connection, API latency, WS streams, freshness timer, bandwidth, alert count. 2. Wire click actions to diagnostics/alerts surfaces. | Status bar reflects live system health and matches documented behavior in Vision/specs. | `tui/ui/status_bar.py`, `tui/app.py`, `tui/streaming.py`, `tests/ui/*` | L | Partial - added live health line (connection/API/WS/freshness/bandwidth/alerts), periodic snapshot updates, diagnostics/alerts click actions, and tests; remaining work is richer degraded-state UX and panel-level drilldowns. |
| TT-114 | Alert sidebar/panel completion | 1. Finalize alert panel rendering and navigation. 2. Wire mute/clear/settings flows and severity styling. 3. Add integration tests for panel-level alerts. | Alerts are visible, actionable, and test-covered across all core profiles. | `tui/widgets/alert_panel.py`, `tui/state/alerts.py`, `tui/ui/screens/*`, `tests/alerts/*` | M | Not started |
| TT-115 | MVP visualization fidelity pass | 1. Ensure required MVP visuals are present: sparklines, orderbook depth bars, funding heatmap, whale flow bars, liquidation distance bars. 2. Add rendering tests for each visual primitive. | Each MVP visualization from Vision Phase 1 is implemented and test-verified in at least one profile panel. | `tui/widgets/*.py`, `tui/tui.css`, `tests/widgets/*`, `tests/ui/*` | L | Not started |
| TT-116 | Command UX parity and keybinding integrity | 1. Validate reserved key behavior and conflict detection. 2. Improve context-aware suggestions/history/fuzzy behavior against Vision expectations. | Command UX behaviors are documented, test-covered, and match default keybinding contract. | `commands/parser.py`, `commands/registry.py`, `tui/ui/widgets/command_palette.py`, `tests/commands/*`, `tests/ui/test_command_palette.py` | M | Not started |

---

### Epic 20 - Governance, Security, and Release Readiness 🔐

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-117 | Canonical-doc alignment and traceability | 1. Ensure canonical Vision docs are present and referenced consistently (`BtheVision_v1_5_5.txt`, `FtheVision_v1_5_5.txt`). 2. Add requirement trace matrix from Vision/specs to tests. | Contributors can trace each required feature to code/tests; no ambiguity in canonical docs pathing. | `AGENTS.md`, `README.md`, `IMPLEMENTATION_PLAN.md`, `docs/*` | S | Not started |
| TT-118 | Release gates and "working MVP" checklist | 1. Define a release gate script for pytest + lint + mypy + integrity gate + UI smoke. 2. Add a pre-release checklist aligned with PRD non-goals and safety constraints. | "Working MVP" means reproducible gate pass plus manual profile smoke checks with no runtime exceptions. | `tools/`, `.github/workflows/*`, `README.md`, `docs/*` | M | Not started |

## Definition of Done (rebaselined)

- Full test suite passes from clean checkout: `pytest -q`.
- Static quality gates pass: `ruff`, `mypy`, and `python tools/data_integrity_gate.py --root .`.
- Profile smoke tests verify every tab/panel can be opened without runtime exceptions.
- Status bar, alerts, and command UX match documented Vision behavior at MVP level.
- Backtesting/provenance determinism checks pass in CI.
- No violations of PRD/AGENTS guardrails (local-first, no synthetic production data, no financial advice/live execution defaults).
