# Hyperliquid Quant Terminal — Command Cheatsheet

This reference enumerates all commands exposed by the TUI application. Commands are grouped by context and panel. All commands operate locally and do not provide financial advice or live trading.

---

## App Lifecycle Commands (Global)
- `:quit` — Exit the application
- `:reload` — Reload configuration and refresh all panels
- `:profile <name>` — Switch dashboard profile (e.g., DayTrader, LiquidationHunter)
- `:theme <name>` — Switch UI theme (Dark Pro, Cyberpunk, Minimal)

## Navigation Commands (Global)
- `:sidebar` — Toggle sidebar visibility
- `:panel <name>` — Focus or open a specific panel
- `:fullscreen` — Toggle fullscreen mode for active panel
- `:tab <name>` — Switch to tabbed panel view
- `:grid` — Toggle grid layout mode

## Data Loading & Refresh Commands
- `:load <stream>` — Load a data stream (e.g., whale, liq, funding)
- `:refresh` — Refresh all data streams
- `:watchlist <coin1,coin2,...>` — Set or update watchlist
- `:anomaly` — Run anomaly detection on watchlist coins

## Backtest & Monte Carlo Commands
- `:backtest <strategy>` — Run backtest with specified strategy
- `:mc <strategy>` — Run Monte Carlo stress test
- `:bt_export <format>` — Export backtest results (CSV, Parquet, JSON)
- `:mc_export <format>` — Export Monte Carlo results (CSV, Parquet, JSON)

## Export Commands (Local-Only)
- `:export <panel> <format>` — Export panel data locally
- `:log_export` — Export logs for current session

## Debug & Inspection Commands
- `:inspect <panel>` — Show panel diagnostics
- `:metrics <panel>` — Display panel metrics and KPIs
- `:errors` — Show recent errors and warnings
- `:config` — Display current configuration

---
All commands are implementation-defined per Vision. For details, see BtheVision_v1_5_5.txt and FtheVision_v1_5_5.txt.