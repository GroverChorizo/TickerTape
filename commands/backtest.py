"""Backtest commands for the CLI/TUI."""

from __future__ import annotations

from typing import Optional

from backtesting.runner import run_from_file


def backtest_run_command(args: list[str]) -> str:
    """Minimal command parser: `run <strategy_path> [--seed N]`"""
    if not args or args[0] != "run":
        return "Usage: :backtest run <strategy_path> [--seed N]"
    if len(args) < 2:
        return "Error: missing strategy_path"
    path = args[1]
    seed: Optional[int] = None
    if "--seed" in args:
        try:
            i = args.index("--seed")
            seed = int(args[i + 1])
        except Exception:
            return "Error: invalid seed"
    try:
        result = run_from_file(path, prices=[100.0, 101.0, 102.0, 103.0], seed=seed)
    except Exception as e:
        return f"Backtest failed: {e}"
    return f"Backtest complete (run_id={result.run_id}) | return={result.metrics.get('return')}"
