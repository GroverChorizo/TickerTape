# TickerTape Requirement Trace Matrix

Maps each Vision requirement → implementation file → test file(s).

Vision sources:
- `docs/BtheVision_v1_5_5.txt` — backend
- `docs/FtheVision_v1_5_5.txt` — frontend

---

## Backend Requirements

| Req ID | Description | Implementation | Tests |
|--------|-------------|----------------|-------|
| B-01 | Hyperliquid REST ingestion | `providers/hyperliquid_client.py`, `tui/providers/hyperliquid.py` | `tests/feeds/test_feed_adapter_kwargs.py` |
| B-02 | WebSocket streaming supervisor | `tui/streaming.py` | `tests/feeds/test_market_data_ticks.py` |
| B-03 | Dataset registry / storage | `src/backend/storage.py` | `tests/` |
| B-04 | Feed base + status contracts | `tui/feeds/base.py` | `tests/feeds/test_profile_feed_contracts.py`, `tests/feeds/test_feed_fallbacks.py` |
| B-05 | Feed fallback (error/empty rendering) | `tui/widgets/*_panel.py` | `tests/feeds/test_feed_fallbacks.py` |
| B-06 | Backtest engine + result schema | `src/tickertape/core/backtesting.py`, `backtesting/job.py` | `tests/backtesting/` |
| B-07 | Monte Carlo return resampling | `backtesting/monte_carlo.py` | `tests/backtesting/` |
| B-08 | Walk-forward validation | `backtesting/walk_forward.py` | `tests/backtesting/` |
| B-09 | Research job queue | `tui/state/research.py` | `tests/backtesting/` |
| B-10 | Data integrity gate | `tools/data_integrity_gate.py` | (self-testing script) |
| B-11 | Secrets / config hygiene | `src/backend/secrets.py`, `config/secrets.py` | `tests/config/` |

---

## Frontend Requirements

| Req ID | Description | Implementation | Tests |
|--------|-------------|----------------|-------|
| F-01 | Multi-screen TUI app | `tui/app.py` | `tests/ui/test_layout.py` |
| F-02 | BaseScreen + sidebar nav | `tui/ui/screens/base.py`, `tui/ui/sidebar.py` | `tests/ui/test_sidebar.py` |
| F-03 | Day Trader profile screen | `tui/ui/screens/profile_day_trader.py` | `tests/ui/test_day_trader_layout.py` |
| F-04 | Liquidation Hunter profile screen | `tui/ui/screens/profile_liquidation.py` | `tests/ui/test_liquidation_layout.py` |
| F-05 | Whale Watcher profile screen | `tui/ui/screens/profile_whale_watcher.py` | `tests/ui/test_whale_watcher_layout.py` |
| F-06 | Funding Arbitrage profile screen | `tui/ui/screens/profile_funding_arbitrage.py` | `tests/ui/test_funding_arbitrage_layout.py` |
| F-07 | Research / Jobs screen | `tui/ui/screens/research.py` | (smoke: `tests/ui/test_profile_tab_switch_smoke.py`) |
| F-08 | Alert sidebar section (6 categories) | `tui/widgets/alert_panel.py`, `tui/ui/sidebar.py` | `tests/ui/test_sidebar.py` |
| F-09 | StatusBar health indicators | `tui/ui/status_bar.py` | `tests/ui/test_status_bar.py` |
| F-10 | Degraded WS state in status bar | `tui/ui/status_bar.py` | `tests/ui/test_status_bar.py` |
| F-11 | Command registry + command bar | `tui/core/commands.py`, `tui/ui/widgets/command_bar.py` | `tests/commands/` |
| F-12 | Sparkline render utility | `tui/render/sparkline.py` | (unit usage in panels) |
| F-13 | Equity curve sparkline in BacktestPanel | `tui/widgets/backtest_panel.py` | `tests/backtesting/` |
| F-14 | Monte Carlo fan chart panel | `tui/widgets/monte_carlo_panel.py` | — |
| F-15 | Fullscreen / density toggle | `tui/ui/fullscreen.py`, `tui/ui/density.py` | `tests/ui/test_fullscreen_density.py` |
| F-16 | Theme manager | `tui/themes/theme_manager.py` | `tests/ui/test_theme_css.py` |
| F-17 | Custom dashboard save/load | `tui/ui/custom_dashboard.py` | `tests/ui/test_custom_dashboard.py` |
| F-18 | Keybinding conflict-free screens | `tui/ui/screens/` | `tests/ui/test_keybinding_conflicts.py` |
| F-19 | Tab carousel navigation | `tui/ui/tab_carousel.py` | `tests/ui/test_tab_carousel.py` |
| F-20 | Settings screen | `tui/ui/screens/settings.py` | `tests/ui/test_settings.py` |

---

## Release Gate

| Gate | Command | File |
|------|---------|------|
| All gates (one command) | `python tools/release_gate.py` | `tools/release_gate.py` |
| Unit + integration tests | `python -m pytest -q` | `tests/` |
| Lint | `python -m ruff check .` | (ruff config in `pyproject.toml`) |
| Type check | `python -m mypy .` | (mypy config in `pyproject.toml`) |
| Data integrity | `python tools/data_integrity_gate.py --root .` | `tools/data_integrity_gate.py` |

---

*Last updated: 2026-03-27*
