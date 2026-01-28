"""Simple backtest result panel."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from backtesting.models import BacktestResult


@dataclass
class BacktestPanel:
    result: BacktestResult

    def summary_lines(self) -> List[str]:
        return [
            f"run_id: {self.result.run_id}",
            f"points: {len(self.result.equity_curve)}",
            f"start: {self.result.metrics.get('start')}",
            f"end: {self.result.metrics.get('end')}",
            f"return: {self.result.metrics.get('return')}",
        ]

    def equity_series(self) -> List[float]:
        return list(self.result.equity_curve)
