# Backtesting & Monte Carlo Specification

## Purpose

Provide a robust research engine for running historical backtests, Monte Carlo simulations and walk‑forward analyses.  The engine must be deterministic, reproducible and flexible enough to support custom user strategies defined in Python【559642516903170†L2-L13】.

## Functional Requirements

* **Strategy Interface** – User‑supplied strategies must accept validated Pandas DataFrames and return signals, trades and metrics【559642516903170†L11-L16】.  The system will validate the presence of required columns and type hints.
* **Backtest Engine** – Execute strategies over historical data with no lookahead bias.  Compute trades, equity curve, P&L, risk metrics (Sharpe, Sortino, drawdown) and generate a trade journal.  Execution must be deterministic; no randomness or external calls【559642516903170†L18-L26】.
* **Monte Carlo Simulation** – Produce multiple randomised equity trajectories by bootstrapping or resampling returns, respecting original distributions.  Provide fan chart plots (P5/P50/P95) and summary statistics【438442747367044†L238-L239】.
* **Walk‑Forward Testing** – Optional module that splits data into rolling train/test windows and reports out‑of‑sample performance (OOS Sharpe, drawdown).  The sample in theVision demonstrates how to report average train/test Sharpe and degradation【438442747367044†L1401-L1405】.
* **Export** – Allow local export of results (equity curves, trade lists, metrics) in CSV, Parquet or JSON format via commands (`:bt_export`, `:mc_export`)【582740865907269†L25-L33】.
* **Engine Settings** – Users can adjust slippage, transaction costs, position sizing and fee models; provide sensible defaults.  Use seedable random number generators for Monte Carlo to allow reproducibility【559642516903170†L18-L26】.

## Non‑Functional Requirements

* **Determinism & Reproducibility** – All backtests and simulations must be reproducible given the same random seed and inputs【559642516903170†L18-L26】.
* **Performance** – Backtests of typical intraday strategies should complete within 10 seconds; Monte Carlo (1000 runs) should finish within 30 seconds on consumer hardware【980693054436426†L31-L33】.
* **Transparency** – Document formulas, metrics and engine internals.  Provide a `:inspect backtest` command to display engine diagnostics and configuration【582740865907269†L36-L38】.

## Implementation Notes

* Implement the backtest engine under `backtesting/engine.py` and Monte Carlo under `backtesting/monte_carlo.py`.
* Use typed models for signals, trades and metrics; ensure consistent units (e.g., basis points, percentages).
* Provide fixtures in `tests/backtesting` with simple strategies to verify engine correctness.
* Integrate with the UI by providing a dedicated backtest panel that visualises equity curves and drawdowns (Sparklines/area charts)【438442747367044†L427-L477】.
