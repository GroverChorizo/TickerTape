# Implementation Plan

This plan enumerates the work required to realise the MVP of the **TickerTape** terminal application.  It is derived from theVision documents and the specifications in the `specs/` directory.  Tasks are organised by **Epic → Story → Task**.  Each task includes acceptance criteria, estimated complexity and files likely to be touched.  Complete one task at a time and run validation gates (tests, lint, type‑check) after each.

## Epics and Stories

### Epic 1 – Project Setup & Scaffolding

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity |
|----|-------|-------|--------------------|---------------|------------|
| TT-001 | Repository scaffolding | 1. Initialize `profiles/`, `providers/`, `validators/`, `backtesting/`, `ui/`, `commands/` packages with `__init__.py` files.<br>2. Create base classes: `Profile` (in `profiles/base.py`), `Provider` (in `providers/base.py`), `Validator` (in `validators/base.py`), `Panel` (in `ui/panel.py`), and `Command` registry. | All packages exist with base classes defined; the app can import these without errors. | New files; updates to `setup.py` or `pyproject.toml` if needed. | S |
| TT-002 | Build test harness | 1. Configure pytest with a `tests/` directory.<br>2. Add example test for a dummy validator.<br>3. Ensure `pytest` runs successfully. | `pytest` collects and runs dummy tests without failure. | `tests/conftest.py`, `tests/test_dummy.py` | S |

| TT-003 | Secrets file management | 1. Define a configuration specification for a secrets file.  By default, look for `~/.ticker_tape/secrets.yaml` (or `.secrets`) but allow the path to be overridden via an environment variable or command‑line argument.<br>2. Modify the startup sequence and wizard to create this file if it does not exist and inform the user of its location.  Populate the file with placeholders for API keys and ensure it is ignored by version control.<br>3. Provide a CLI command `:secrets` to print the secrets file path and open it in an editor. | Running the app without specifying a secrets path creates the default secrets file and logs its path.  The command `:secrets` prints the path and opens the file.  Unit tests verify creation and reading of the secrets file. | `config/secrets.py`, `ui/wizard.py`, `commands/secrets.py`, `tests/config/test_secrets.py` | M |

| TT-004 | CLI entry points | 1. Configure the build system (`pyproject.toml` or `setup.py`) to expose console scripts named `TickerTape` and `TTape` that run the application’s main entry point.<br>2. Update AGENTS.md or README.md to document the new commands and remove references to `python -m ticker_tape` where appropriate. | After installation, running `TickerTape` or `TTape` launches the application.  A test running these commands via subprocess succeeds. | `pyproject.toml` or `setup.py`, `docs/README.md` or `AGENTS.md`, `tests/test_cli_entrypoints.py` | S |

### Epic 2 – Data Provider Layer

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity |
|----|-------|-------|--------------------|---------------|------------|
| TT-010 | Provider abstraction | 1. Define `Provider` interface in `providers/base.py` with methods for ticks, order book, liquidations, whale trades, funding rates and positions.<br>2. Create typed data models (`Tick`, `OrderBookLevel`, `LiquidationEvent`, `WhaleTrade`, `FundingRate`, `Position`) in `providers/models.py`. | Interface methods and models are defined with type hints; unit tests import them without errors. | `providers/base.py`, `providers/models.py` | M |
| TT-011 | Hyperliquid provider | 1. Implement `HyperliquidProvider` in `providers/hyperliquid.py` adhering to the base interface.<br>2. Use HTTP/WS endpoints from the Hyperliquid Data Layer API with timeouts, retries and backoff【438442747367044†L104-L116】.<br>3. Cache snapshots in memory; return typed models. | Provider returns correct data for at least one endpoint; snapshot caching works in unit tests. | `providers/hyperliquid.py`, `tests/providers/test_hyperliquid.py` | L |
| TT-012 | Provider diagnostics | 1. Implement a diagnostic helper (e.g., `providers/diagnostics.py`) that checks connectivity and returns a summary (HTTP latency, WS state, last update).<br>2. Expose a command `:diagnose provider`. | Running the command prints a report with latency values; unit test covers typical case. | `providers/diagnostics.py`, `commands/diagnose.py`, `tests/providers/test_diagnostics.py` | S |

### Epic 3 – Data Validation

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity |
|----|-------|-------|--------------------|---------------|------------|
| TT-020 | Validator framework | 1. Create abstract `Validator` base class in `validators/base.py` with a `validate()` method returning a `ValidationReport`.<br>2. Define `ValidationReport` dataclass with error/warning counts and details.<br>3. Register validators via a registry. | Base class and registry work; unit tests can register and run a dummy validator. | `validators/base.py`, `validators/registry.py`, `validators/report.py`, `tests/validators/test_registry.py` | M |
| TT-021 | Core validators | Implement built‑in validators:
   - `SchemaValidator`
   - `MissingnessValidator`
   - `RangeValidator` (with funding rate bounds【438442747367044†L104-L116】)
   - `MonotonicValidator`
   - `DuplicateValidator`
   - `OutlierValidator`
Add unit tests using fixture data. | Each validator correctly identifies violations; tests cover success and failure cases. | `validators/schema.py`, `validators/missingness.py`, etc.; `tests/validators/test_*` | L |
| TT-022 | Validation command | 1. Add a CLI command `:validate <dataset>` that runs all validators on the specified snapshot and displays a summary table.<br>2. Implement UI integration in a modal window. | Running the command on a fixture dataset prints a validation summary; unit test verifies output. | `commands/validate.py`, `ui/validate_panel.py`, `tests/commands/test_validate.py` | M |

### Epic 4 – Profile Modules

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity |
|----|-------|-------|--------------------|---------------|------------|
| TT-030 | Day Trader profile | 1. Create `profiles/day_trader.py` implementing the profile interface.<br>2. Register four panels (Price Chart, Top Positions, Whale Flow, Liquidation Stats) with default data streams.【438442747367044†L244-L252】【438442747367044†L274-L283】<br>3. Add watchlist management and anomaly detection. | The Day Trader screen loads with four panels and updates from live data; watchlist command works in tests. | `profiles/day_trader.py`, `ui/panels/*`, `commands/watchlist.py`, `tests/profiles/test_day_trader.py` | L |
| TT-031 | Liquidation Hunter profile | 1. Implement `profiles/liquidation_hunter.py` with panels: Liquidation Heatmap, Liquidation Distance, Cascade Monitor【438442747367044†L274-L283】【438442747367044†L62-L89】.<br>2. Implement cascade detection helper and thresholds. | Screen displays heatmap and progress bars; cascade alerts trigger correctly in tests. | `profiles/liquidation_hunter.py`, `ui/panels/liquidation_heatmap.py`, `ui/panels/liquidation_distance.py`, `tests/profiles/test_liquidation_hunter.py` | L |
| TT-032 | Whale Watcher profile | 1. Implement `profiles/whale_watcher.py` with panels: Whale Trade List, Directional Flow Bars, Whale Heatmap【438442747367044†L384-L392】.<br>2. Add wallet inspection functionality for selected addresses【438442747367044†L1768-L1773】.<br>3. Implement search filters for size and side【438442747367044†L1719-L1727】. | Screen updates with real‑time trades; selecting a wallet opens the wallet panel; tests cover UI and data. | `profiles/whale_watcher.py`, `ui/panels/whale_list.py`, `ui/panels/whale_flow.py`, `ui/panels/wallet_panel.py`, `tests/profiles/test_whale_watcher.py` | L |
| TT-033 | Funding Arbitrageur profile | 1. Create `profiles/funding_arbitrageur.py` with panels: Funding Heatmap, Funding Extremes, Arbitrage Comparison【438442747367044†L342-L359】【438442747367044†L1620-L1636】.<br>2. Implement arbitrage detection logic with thresholds【438442747367044†L1656-L1672】.<br>3. Provide commands to add/remove exchanges. | Screen shows heatmap and comparison table; arbitrage alerts fire on test data; tests ensure detection logic is correct. | `profiles/funding_arbitrageur.py`, `ui/panels/funding_heatmap.py`, `ui/panels/funding_extremes.py`, `ui/panels/funding_comparison.py`, `tests/profiles/test_funding_arbitrageur.py` | L |

### Epic 5 – Backtesting & Simulation Engine

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity |
|----|-------|-------|--------------------|---------------|------------|
| TT-040 | Backtest engine | 1. Implement core engine that runs strategies over historical data with no lookahead bias【559642516903170†L18-L26】.<br>2. Compute equity curve, trades, P&L and risk metrics. 3. Return a `BacktestResult` object. | Engine processes a sample strategy and produces correct metrics; tests compare with expected values. | `backtesting/engine.py`, `backtesting/models.py`, `tests/backtesting/test_engine.py` | L |
| TT-041 | Monte Carlo simulation | 1. Implement Monte Carlo runner that bootstraps returns and produces a set of equity trajectories【438442747367044†L238-L239】.<br>2. Output fan chart data and summary stats. | Running Monte Carlo on a fixture dataset produces expected percentiles; tests verify reproducibility. | `backtesting/monte_carlo.py`, `tests/backtesting/test_monte_carlo.py` | M |
| TT-042 | Walk‑Forward testing | 1. Implement walk‑forward module that splits data into train/test windows and executes strategies.【438442747367044†L1401-L1405】<br>2. Compute average train/test metrics and degradation. | Module returns a report summarising OOS Sharpe and degradation; tests validate outputs on fixture data. | `backtesting/walk_forward.py`, `tests/backtesting/test_walk_forward.py` | M |
| TT-043 | Strategy integration | 1. Add ability for users to load custom strategy modules from a file path.【559642516903170†L18-L26】<br>2. Validate that strategies implement the required interface. | Loading an example strategy file triggers correct backtest results; tests cover invalid strategies. | `commands/backtest.py`, `backtesting/loader.py`, `tests/backtesting/test_loader.py` | M |
| TT-044 | Backtest UI | 1. Implement a backtest panel that displays equity curves and drawdowns using sparklines or area charts【438442747367044†L427-L477】.<br>2. Integrate with command system (`:backtest`). | Running a backtest via command opens a panel with results; tests include UI assertions. | `ui/panels/backtest.py`, `commands/backtest.py`, `tests/ui/test_backtest_panel.py` | L |

### Epic 6 – User Interface & Layout

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity |
|----|-------|-------|--------------------|---------------|------------|
| TT-050 | Layout manager | 1. Implement responsive layout logic with breakpoints for ultra‑wide, wide, standard, narrow and compact modes【438442747367044†L553-L659】.<br>2. Support separate screens per profile and switching between them. | Changing terminal width triggers correct layout adjustments in tests; switching profiles changes the entire view. | `ui/layout.py`, `ui/screens.py`, `tests/ui/test_layout.py` | L |
| TT-051 | Panel framework | 1. Create a `Panel` base class with states (focused, alert) and built‑in animations【438442747367044†L784-L799】.<br>2. Implement common panel widgets (tables, heatmaps, bar charts, sparkline charts). | Panels render correctly in isolation; tests cover focus transitions and alert flashing. | `ui/panels/base.py`, `ui/widgets/*.py`, `tests/ui/test_panel_framework.py` | L |
| TT-052 | Theming & styles | 1. Define CSS styles for each theme (cypherpunk, Dark Pro, Matrix, Minimal).<br>2. Implement accent colours and spacing system【438442747367044†L1394-L1395】.<br>3. Provide commands to switch themes (`:theme cypherpunk`). | Switching themes updates colours across the UI; tests verify style variables. | `ui/themes/*.css`, `commands/theme.py`, `tests/ui/test_theme.py` | M |
| TT-053 | Sidebar & tabs | 1. Implement responsive sidebar with icon‑only mode; create bottom tab bar for narrow screens【438442747367044†L614-L632】. | Sidebar collapses appropriately; tests verify tab switching. | `ui/sidebar.py`, `ui/tabbar.py`, `tests/ui/test_sidebar.py` | M |
| TT-054 | Fullscreen & density | 1. Add fullscreen toggle for panels (F key) and density mode toggle (D key)【438442747367044†L685-L723】【438442747367044†L929-L943】.<br>2. Persist user choice per session. | Pressing F and D toggles states correctly; tests cover persistence. | `ui/fullscreen.py`, `ui/density.py`, `tests/ui/test_fullscreen_density.py` | S |

| TT-055 | Panel resizing & custom dashboards | 1. Enhance the panel framework to support drag‑resize handles on each panel.  Users can click and drag to adjust panel width and height within the grid.<br>2. Implement a dashboard customization workflow accessible from the Settings panel or wizard: allow users to create new profiles, choose panels to include, arrange them via drag‑and‑drop, and save the layout as a named profile.<br>3. Persist custom dashboards to the user’s config directory (`~/.ticker_tape/`), and load them on start.<br>4. Ensure resizing and layout changes update the underlying grid and remain consistent across theme and density modes. | Panels can be resized interactively in the TUI; new custom profiles can be created, saved and loaded; unit tests simulate drag resizing and verify persisted layout. | `ui/panels/base.py`, `ui/layout.py`, `ui/custom_dashboard.py`, `config/config.py`, `tests/ui/test_panel_resizing.py`, `tests/ui/test_custom_dashboard.py` | L |

| TT-056 | Tab carousel & breadcrumb navigation | 1. Implement a navigation component (e.g., `ui/tab_carousel.py`) that lists all open screens/panels and allows users to cycle through them with keyboard shortcuts (e.g., `Ctrl+Tab`/`Shift+Ctrl+Tab`).<br>2. Provide a visual breadcrumb trail or status bar indicating the current position in the carousel and the number of open windows.<br>3. Integrate the carousel with detached panels and multi‑window mode, allowing smooth navigation across separate terminal windows.<br>4. Persist the list of open windows and restore the navigation order on restart. | When multiple screens are open, users can cycle through them using the carousel; the breadcrumb shows the current position; tests cover navigation and persistence. | `ui/tab_carousel.py`, `ui/status_bar.py`, `ui/layout.py`, `tests/ui/test_tab_carousel.py`, `tests/ui/test_navigation_persistence.py` | M |

### Epic 7 – Command System

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity |
|----|-------|-------|--------------------|---------------|------------|
| TT-060 | Command parser & registry | 1. Implement command registry and parser to handle command definitions with arguments and options. 2. Provide error feedback for invalid commands.【438442747367044†L1707-L1735】【582740865907269†L6-L40】 | Parser can register commands and parse sample strings; tests cover error conditions. | `commands/parser.py`, `commands/registry.py`, `tests/commands/test_parser.py` | M |
| TT-061 | Command palette UI | 1. Implement `CommandPalette` widget that shows suggestions, history and syntax hints【438442747367044†L1707-L1735】.<br>2. Integrate palette invocation ( `/` or `Ctrl+K` ). | Opening the palette displays suggestions; fuzzy search works; tests simulate user input. | `ui/command_palette.py`, `tests/ui/test_command_palette.py` | L |
| TT-062 | Built‑in commands | Implement global, navigation, data, backtest/MC, export, debug commands as per the command specification【582740865907269†L6-L40】. | Running each command performs its expected action; tests cover success and failure scenarios. | `commands/*.py`, `tests/commands/test_commands.py` | L |

### Epic 8 – Startup Wizard & Settings

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity |
|----|-------|-------|--------------------|---------------|------------|
| TT-070 | Wizard flow | 1. Implement multi‑step wizard with screens: Welcome, Profile Selection, Theme Selection, Dashboard Customization, Alerts Configuration, Completion【438442747367044†L1431-L1583】.<br>2. Implement state machine to move between steps. 3. Persist selections to a config file. | Running the wizard from a fresh install guides the user through all steps; selections are stored and loaded on next launch. | `ui/wizard.py`, `config/config.py`, `tests/ui/test_wizard.py` | L |
| TT-071 | Settings panel | 1. Implement a Settings screen accessible via `Ctrl+,` that allows users to change profile, theme, panels and alerts【438442747367044†L1561-L1583】.<br>2. Save changes to config and update UI accordingly. | Changing settings updates the application without restart; tests confirm persistence. | `ui/settings.py`, `tests/ui/test_settings.py` | M |

### Epic 9 – Multi‑Exchange Funding Panel

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity |
|----|-------|-------|--------------------|---------------|------------|
| TT-080 | Multi‑exchange panel | 1. Implement panel that displays funding rates across exchanges with computed spread and arbitrage flag【438442747367044†L1620-L1636】.<br>2. Implement arbitrage detection logic using thresholds【438442747367044†L1656-L1672】.<br>3. Provide commands to add/remove exchanges and to refresh data. | Panel renders correctly with sample data; detection logic flags opportunities; tests verify. | `ui/panels/multi_exchange_funding.py`, `providers/external.py`, `commands/exchange.py`, `tests/panels/test_multi_exchange.py` | M |

### Epic 10 – Alerts & Notifications

| ID | Story | Tasks | Acceptance Criteria | Files Touched | Complexity |
|----|-------|-------|--------------------|---------------|------------|
| TT-090 | Alert framework | 1. Implement global alert service that can queue and dispatch alerts with severity levels (info, warning, critical, urgent)【438442747367044†L1044-L1113】.<br>2. Define alert configuration (enabled events, thresholds) and persistence. | Alerts triggered by other modules display pop‑ups with correct colour coding; user can mute or clear alerts. | `alerts/service.py`, `ui/alerts.py`, `tests/alerts/test_service.py` | M |
| TT-091 | Panel integration | Integrate alert triggers in panels: cascade alerts, whale trade alerts, funding extreme alerts and anomaly alerts【438442747367044†L62-L89】【438442747367044†L155-L180】. | When events exceed thresholds, the corresponding alert appears; tests simulate events. | `profiles/*`, `ui/panels/*`, `tests/alerts/test_integration.py` | L |

## Definition of Done

* All tasks in the MVP epics (1–10) are complete and marked as done.
* All unit tests, type checks and linting pass (run via `pytest`, `mypy`, `ruff/flake8`).
* The application starts, displays the startup wizard and allows the user to run through the wizard, switch profiles and load panels.
* The command palette executes core commands without errors.
* Backtest engine produces deterministic results on fixture strategies.
* Multi‑exchange funding panel identifies an arbitrage on test data.
* Alert pop‑ups appear for cascade, whale and funding events.
