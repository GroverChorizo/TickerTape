# Command System Specification

## Purpose

Define the design and behaviour of the command‑driven interface that powers navigation, data operations and backtesting within the terminal.  Commands allow users to interact with the system efficiently without leaving the keyboard.

## Functional Requirements

* **Command Palette** – Press `/` or `Ctrl+K` to open a modal overlay that dims the dashboard【438442747367044†L1707-L1735】.  It should support fuzzy search, tab‑based autocompletion and command history navigation (Up/Down)【438442747367044†L1707-L1735】.
* **Global Commands** – Provide lifecycle commands such as `:quit` (exit), `:reload` (reload config) and `:profile <name>` to switch profiles【582740865907269†L6-L11】.
* **Navigation Commands** – Commands to focus or open panels (e.g., `:panel whales`), toggle fullscreen (`:fullscreen`), toggle sidebar (`:sidebar`), switch tabs (`:tab <name>`) and change grid layout (`:grid`)【582740865907269†L12-L18】.
* **Data Commands** – Commands to load or refresh data streams (`:load whales`, `:refresh`), set watchlists (`:watchlist BTC,ETH`), and run anomaly detection (`:anomaly`)【582740865907269†L19-L24】.
* **Backtest & Monte Carlo Commands** – Commands to run backtests and Monte Carlo tests (`:backtest <strategy>`, `:mc <strategy>`), export results (`:bt_export csv`, `:mc_export json`)【582740865907269†L25-L29】.
* **Export Commands** – Commands to export panel data or logs locally (`:export <panel> csv`, `:log_export`)【582740865907269†L31-L34】.
* **Debug & Inspection Commands** – Commands to inspect panel diagnostics, view metrics, show errors or display current config (`:inspect whales`, `:metrics funding`, `:errors`, `:config`)【582740865907269†L35-L40】.
* **Search Within Panel** – While a panel is focused, pressing `/` should begin a search within that panel; the search syntax is described in theVision (e.g., `/search btc >1M sell`)【438442747367044†L1719-L1727】.

## Non‑Functional Requirements

* **Discoverability** – Typing `?` or pressing `F1` should show context‑aware help with a list of available commands and short descriptions【438442747367044†L1298-L1357】.
* **Extensibility** – Commands should be registered via a registry (e.g., `commands.register(name, handler, description)`) so new modules can add their own commands without modifying core code.
* **Conflict Handling** – Reserved keys such as `/`, `Ctrl+K`, `Ctrl+Q` and `Tab` cannot be re‑bound【438442747367044†L1298-L1370】.  When a user attempts to assign a conflicting key, the system must warn them and disable the duplicate binding.

## Implementation Notes

* Implement command parsing in `commands/parser.py` and registration in `commands/registry.py`.
* Provide a `CommandPalette` widget in `ui/command_palette.py` that implements fuzzy search and displays suggestions, history and syntax hints.
* Use Python’s `argparse` or a custom parser to handle arguments and options for commands; ensure clear error messages on invalid usage.
