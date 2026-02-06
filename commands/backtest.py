"""Backtest commands for the CLI/TUI."""

from __future__ import annotations

from typing import Optional

import json
from pathlib import Path

from backtesting.runner import run_from_file


def backtest_run_command(args: list[str]) -> str:
    """Command parser: `run <strategy_path> --prices <path.json> [--seed N] --confirm`"""
    if not args or args[0] != "run":
        return "Usage: :backtest run <strategy_path> --prices <path.json> [--seed N] --confirm"
    if len(args) < 2:
        return "Error: missing strategy_path"
    path = args[1]
    seed: Optional[int] = None
    prices_path: Optional[Path] = None
    if "--seed" in args:
        try:
            i = args.index("--seed")
            seed = int(args[i + 1])
        except Exception:
            return "Error: invalid seed"
    if "--prices" in args:
        try:
            i = args.index("--prices")
            prices_path = Path(args[i + 1])
        except Exception:
            return "Error: invalid --prices usage"
    if prices_path is None:
        return "Error: missing --prices path (no synthetic defaults allowed)"
    if "--confirm" not in args and "--allow-exec" not in args:
        return "Refusing to run strategy without --confirm. This executes local code."
    try:
        prices_payload = json.loads(prices_path.read_text(encoding="utf-8"))
        prices = prices_payload if isinstance(prices_payload, list) else prices_payload.get("prices")
        if not isinstance(prices, list):
            return "Error: --prices file must contain a JSON list or {'prices': [...]}."
        result = run_from_file(path, prices=prices, seed=seed, confirm_exec=True)
    except Exception as e:
        return f"Backtest failed: {e}"
    return f"Backtest complete (run_id={result.run_id}) | return={result.metrics.get('return')}"
