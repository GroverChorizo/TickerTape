"""Backtesting dataclasses and models."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Any


@dataclass
class BacktestResult:
    run_id: str
    timestamps: List[int]
    equity_curve: List[float]
    metrics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BacktestJobMetadata:
    run_id: str
    strategy: str
    strategy_version: str | None
    dataset: str | None
    params: Dict[str, Any]
    seed: int | None
    started_at_ms: int
    finished_at_ms: int | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
