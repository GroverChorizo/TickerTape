"""A minimal backtest runner that executes a simple strategy script.

Strategy contract (minimal): the strategy file must define a function
`run(prices: list[float], seed: int | None) -> list[float]` that returns an
`equity_curve` (list of floats) aligned with prices.
"""

from __future__ import annotations

import os
import time
from typing import List, Optional

from .models import BacktestResult, BacktestJobMetadata
from .job import write_metadata, write_result, new_run_dir
from .loader import run_strategy_file


def run_from_file(
    strategy_path: str,
    prices: List[float],
    *,
    dataset: Optional[str] = None,
    seed: Optional[int] = None,
    run_id: Optional[str] = None,
    job_root: Optional[str] = None,
    confirm_exec: bool = False,
) -> BacktestResult:
    started = int(time.time() * 1000)
    equity_curve = run_strategy_file(
        strategy_path,
        prices,
        seed=seed,
        confirm_exec=confirm_exec,
    )
    finished = int(time.time() * 1000)
    run_id = run_id or os.path.basename(new_run_dir(job_root))

    metadata = BacktestJobMetadata(
        run_id=run_id,
        strategy=os.path.basename(strategy_path),
        strategy_version=None,
        dataset=dataset,
        params={},
        seed=seed,
        started_at_ms=started,
        finished_at_ms=finished,
    )

    result = BacktestResult(
        run_id=run_id,
        timestamps=list(range(len(equity_curve))),
        equity_curve=list(equity_curve),
        metrics={
            "start": equity_curve[0] if equity_curve else 0.0,
            "end": equity_curve[-1] if equity_curve else 0.0,
            "return": (equity_curve[-1] - equity_curve[0]) if equity_curve else 0.0,
        },
    )

    # Persist metadata and result
    write_metadata(metadata, root=job_root or None)
    write_result(result, root=job_root or None)

    return result


__all__ = ["run_from_file"]
