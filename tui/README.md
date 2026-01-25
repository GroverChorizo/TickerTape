# TickerTape TUI

This directory contains the production TUI for TickerTape (Textual-based, local-first).

## Run

From the repository root:

```bash
python -m tui.app
```

## Command Palette

Use the command bar at the bottom for orchestration:

- `/profile <name>`
- `/backtest run --strategy PATH --dataset DATASET --timeframe 1h --param key=value --seed 123`
- `/backtest sweep --strategy PATH --dataset DATASET --timeframe 1h --grid key=1,2 --seed 123`
- `/montecarlo run ...`
- `/walkforward run ...`

If no backtest runner is configured, jobs are recorded as **blocked** with the explicit reason.

## Data Sources

- Liquidation snapshots read from `data/parquet/` using the backend registry.
- Alerts are consumed via the backend alert notifier (default `127.0.0.1:8765`).

TickerTape is research-only: no trading, no execution, no advice.
