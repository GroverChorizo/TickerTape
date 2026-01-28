# Implementation Plan

Last updated: 2026-01-27

This plan enumerates the work required to realize the MVP of the TickerTape terminal application. It is derived from the PRD and the specifications in the `specs/` directory, then reconciled with the current codebase. Tasks are organized by Epic -> Story -> Task. Each task includes acceptance criteria, estimated complexity, likely files, and a status.

## Current State Snapshot

- Multi-screen shell exists: `tui/app.py` with Home screen, Liquidation Hunter screen, and view screens (time/heatmap/table).
- Command system exists in a minimal form: `tui/core/commands.py`, `tui/core/router.py`, and a command bar widget (no palette overlay).
- Hyperliquid provider exists in `tui/providers/hyperliquid.py` using MoonDev API via feed wrappers with polling + backoff; no WS yet.
- Liquidation Hunter data pipeline exists (feed + models + screen + capture status), but missing heatmap/distance/cascade-alert features from the spec.
- Multi-exchange funding feed + panel exist, but arbitrage detection/alerts and profile screen wiring are incomplete.
- Secrets handling is implemented via env file in `src/backend/secrets.py`, not the YAML spec in `specs/config_secrets.md`.

## Gap Analysis Summary (by spec)

- Command System: **Done.** Palette, parser, history and built-in commands are implemented and tested.
- UI Layout: **Done.** Responsive breakpoints, sidebar/tabbar, theming, and panel resizing are implemented.
- Profiles: **Mostly Done.** Day Trader, Liquidation Hunter, Whale Watcher and Funding Arbitrageur profiles exist and have panel scaffolding; minor panel feature wiring remains.
- Liquidation Hunter: **Partial.** Heatmap, distance and cascade monitor are present; **cascade alert wiring into the global alert service and UI is pending.**
- Data Ingestion: **Partial.** Provider interfaces and typed models exist; **Hyperliquid currently provides HTTP snapshots only.** WebSocket streaming, reconnect/backoff, and additional endpoints (orderbook/funding streams) are not implemented.
- Data Validation: **Done.** Validator framework and core validators are implemented with tests.
- Backtesting & Simulation: **Not started / not integrated.** The `backtesting/` package is a placeholder; Monte Carlo and walk‑forward capabilities exist in other repos but are not integrated into the app.
- Secrets: **Done.** YAML secrets handling, CLI integration and wizard support are implemented.
- Alerts & Notifications: **Partial.** Backend `AlertManager` and socket notifier exist and TUI alert stream can receive messages; per‑panel trigger integration and mute/clear UX remain to be implemented.
- Architecture & Quality: **Not started.** Linting/typing hardening, spec ↔ code path alignment, and provider streaming tests are outstanding.

**New priorities:** Add explicit, small tasks for (1) Research job provenance and deterministic job store, (2) Alert UI integration and panel triggers, (3) Hyperliquid WebSocket streaming + test harness, and (4) Minimal backtest runner + deterministic CI tests. These are added below as TT‑095 → TT‑099.

## Epics and Stories

### Epic 1 - Project Setup & Scaffolding

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-001 | Repository scaffolding | 1. Initialize `profiles/`, `providers/`, `validators/`, `backtesting/`, `ui/`, `commands/` packages with `__init__.py` files. 2. Create base classes: `Profile` (in `profiles/base.py`), `Provider` (in `providers/base.py`), `Validator` (in `validators/base.py`), `Panel` (in `ui/panel.py`), and `Command` registry. | All packages exist with base classes defined; the app can import these without errors. | New files; updates to `setup.py` or `pyproject.toml` if needed. | S | Done - base packages and base classes added at repo root. |
| TT-002 | Build test harness | 1. Configure pytest with a `tests/` directory. 2. Add example test for a dummy validator. 3. Ensure `pytest` runs successfully. | `pytest` collects and runs dummy tests without failure. | `tests/conftest.py`, `tests/test_dummy.py` | S | Done - pytest configured, multiple tests present. |
| TT-003 | Secrets file management | 1. Define a configuration specification for a secrets file. By default, look for `~/.ticker_tape/secrets.yaml` (or `.secrets`) but allow the path to be overridden via env var or CLI arg. 2. Modify startup sequence and wizard to create this file if it does not exist and inform the user. 3. Provide a CLI command `:secrets` to print the secrets file path and open it in an editor. | Running the app without specifying a secrets path creates the default secrets file and logs its path. The command `:secrets` prints the path and opens the file. Unit tests verify creation and reading. | `src/config/secrets.py`, `tui/wizard.py`, `tui/app.py`, `tests/config/test_secrets.py` | M | Done - YAML secrets module, CLI command, wizard integration, and tests added. |
| TT-004 | CLI entry points | 1. Configure build system to expose console scripts named `TickerTape` and `TTape` that run the application’s main entry point. 2. Update docs to document new commands. | After installation, running `TickerTape` or `TTape` launches the application. A test running these commands via subprocess succeeds. | `setup.py`, `README.md`, `AGENTS.md`, `tests/test_cli_entrypoints.py` | S | Done - setup.py entry points added with tests and docs updates. |

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
| TT-040 | Backtest engine | 1. Implement core engine that runs strategies over historical data with no lookahead bias. 2. Compute equity curve, trades, P&L and risk metrics. 3. Return a `BacktestResult` object. | Engine processes a sample strategy and produces correct metrics; tests compare with expected values. | `backtesting/engine.py`, `backtesting/models.py`, `tests/backtesting/test_engine.py` | L | Not started |
| TT-041 | Monte Carlo simulation | 1. Implement Monte Carlo runner that bootstraps returns and produces a set of equity trajectories. 2. Output fan chart data and summary stats. | Running Monte Carlo on a fixture dataset produces expected percentiles; tests verify reproducibility. | `backtesting/monte_carlo.py`, `tests/backtesting/test_monte_carlo.py` | M | Not started |
| TT-042 | Walk-forward testing | 1. Implement walk-forward module that splits data into train/test windows and executes strategies. 2. Compute average train/test metrics and degradation. | Module returns a report summarizing OOS Sharpe and degradation; tests validate outputs on fixture data. | `backtesting/walk_forward.py`, `tests/backtesting/test_walk_forward.py` | M | Not started |
| TT-043 | Strategy integration | 1. Add ability for users to load custom strategy modules from a file path. 2. Validate that strategies implement the required interface. | Loading an example strategy file triggers correct backtest results; tests cover invalid strategies. | `commands/backtest.py`, `backtesting/loader.py`, `tests/backtesting/test_loader.py` | M | Not started |
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
| TT-090 | Alert framework | 1. Implement global alert service that can queue and dispatch alerts with severity levels. 2. Define alert configuration (enabled events, thresholds) and persistence. | Alerts triggered by other modules display pop-ups with correct color coding; user can mute or clear alerts. | `src/backend/alerts.py`, `tui/widgets/alert_panel.py`, `tests/alerts/test_service.py` | M | Partial - backend alert server + panel exist, no unified service or new UI integration. |
| TT-091 | Panel integration | Integrate alert triggers in panels: cascade alerts, whale trade alerts, funding extreme alerts and anomaly alerts. | When events exceed thresholds, the corresponding alert appears; tests simulate events. | `tui/widgets/*`, `tests/alerts/test_integration.py` | L | Not started |

### Epic 11 - Architecture Alignment

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-092 | Align spec paths with code structure | 1. Decide whether to migrate to top-level `profiles/`, `providers/`, `ui/`, `commands/` packages or keep the `tui/`-centric layout. 2. Update specs and import paths accordingly. | Specs and code paths agree; new contributors can follow a single structure without guesswork. | `IMPLEMENTATION_PLAN.md`, `specs/*`, potential refactors in `tui/` | S | Not started |
| TT-093 | Linting & typing hardening | 1. Revisit `ruff.toml` and `mypy.ini` to reduce global ignores. 2. Fix outstanding lint/type errors incrementally and align with repo style. | Ruff and mypy run with minimal ignores; remaining suppressions are localized with comments or per-module config. | `ruff.toml`, `mypy.ini`, offending modules | M | Not started |
| TT-094 | Provider streaming & additional endpoints | 1. Add WebSocket streaming support to the Hyperliquid provider with reconnect/backoff. 2. Implement at least one additional endpoint (orderbook or funding) returning typed models. 3. Add tests for WS reconnect and new endpoint parsing. | WS reconnect behavior validated in tests; new endpoint returns typed models; provider remains deterministic. | `providers/hyperliquid.py`, `tests/test_provider_hyperliquid.py` | M | Not started |

---

### Epic 12 - Research Jobs & Provenance 🔧

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-095 | Provenance & job store | 1. Define a `BacktestJob` metadata model capturing: strategy name/version, dataset(s), timeframe(s), parameters, random seed(s), start/end timestamps and result path. 2. Implement a local job store under `~/.ticker_tape/jobs/<run_id>/` that writes metadata and serialized `BacktestResult` in JSON/Parquet. 3. Add CLI commands `:jobs list` and `:jobs show <id>`. | Running a backtest writes a run folder with metadata and result files; `:jobs list` shows recent runs and `:jobs show` prints detailed metadata. Unit tests cover metadata serialization and file layout. | `backtesting/job.py`, `backtesting/store.py`, `commands/jobs.py`, `tests/backtesting/test_jobs.py` | M | Not started |

| TT-096 | Provenance tests & CI | 1. Add unit tests that assert deterministic `BacktestResult` given fixed seed and dataset fixture. 2. Include a lightweight end‑to‑end CI job that runs a sample backtest and compares output checksums to stored golden results. | Tests fail if backtest outputs change; CI job runs in <2 minutes and fails on non‑deterministic output. | `tests/backtesting/test_provenance.py`, `.github/workflows/backtest.yml` | M | Not started |

---

### Epic 13 - Alerts Completion 🔔

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-097 | Alert UI integration & per‑panel triggers | 1. Add alert configuration for panels (enabled events, thresholds, severity). 2. Wire `src/backend/AlertManager` events to panel-level triggers (cascade, whale, funding). 3. Implement mute/clear UX and a `:alerts` command to list recent alerts. | Simulated events generate UI pop-ups and entries in the alert panel; user can mute/clear alerts and `:alerts` lists recent items. Unit and UI tests exercise the flow. | `src/backend/alerts.py`, `tui/state/alerts.py`, `tui/widgets/alert_panel.py`, `tests/alerts/test_integration.py` | L | Not started |

---

### Epic 14 - Provider Streaming & Test Harness 🛰️

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity | Status |
|----|-------|-------|--------------------|---------------|------------|--------|
| TT-098 | Hyperliquid WS streaming & harness | 1. Add an asyncio WebSocket client to `providers/hyperliquid.py` with automatic reconnect/backoff and jitter. 2. Implement streaming handlers for at least orderbook and funding endpoints and ensure typed model emission. 3. Add a local test harness that replays recorded WS frames for deterministic testing. | WS reconnect/backoff behavior validated in unit tests; harness can replay recorded frames to verify parsing and backpressure handling. | `providers/hyperliquid.py`, `tests/test_provider_hyperliquid_ws.py`, `tests/fixtures/hyperliquid/` | M | Not started |

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

## Definition of Done (unchanged)

- All tasks in the MVP epics (1-10) are complete and marked as done.
- All unit tests, type checks and linting pass (run via `pytest`, `mypy`, `ruff/flake8`).
- The application starts, displays the startup wizard and allows the user to run through the wizard, switch profiles and load panels.
- The command palette executes core commands without errors.
- Backtest engine produces deterministic results on fixture strategies.
- Multi-exchange funding panel identifies an arbitrage on test data.
- Alert pop-ups appear for cascade, whale and funding events.
