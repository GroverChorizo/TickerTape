"""Strategy runner invoked in a subprocess."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence


def _load_strategy(path: str):
    spec = importlib.util.spec_from_file_location("__strategy__", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load strategy from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    if not hasattr(mod, "run"):
        raise AttributeError("Strategy file must define a `run(prices, seed)` function")
    return mod


def _validate_equity_curve(curve: Sequence[Any], expected_len: int) -> list[float]:
    out: list[float] = []
    for v in curve:
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            raise ValueError("Equity curve must contain numeric values")
    if expected_len and len(out) != expected_len:
        raise ValueError("Equity curve length must match input price series")
    return out


def main(argv: list[str]) -> int:
    # This module executes arbitrary user code (the strategy file). It must only
    # run when launched through backtesting.loader.run_strategy_file, which sets
    # this flag after an explicit confirm_exec gate. Refuse otherwise.
    if os.environ.get("TICKERTAPE_STRATEGY_EXEC") != "1":
        print(
            "strategy execution not authorized "
            "(missing TICKERTAPE_STRATEGY_EXEC; use backtesting.loader)",
            file=sys.stderr,
        )
        return 2

    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    prices = payload.get("prices") or []
    seed = payload.get("seed")

    mod = _load_strategy(args.strategy)
    equity_curve = mod.run(prices, seed)
    equity_curve = _validate_equity_curve(equity_curve, len(prices))

    Path(args.output).write_text(
        json.dumps({"equity_curve": equity_curve}, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

