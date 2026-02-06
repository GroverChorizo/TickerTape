"""Backtesting dataclasses and models (shim)."""

from tickertape.core.backtesting import (
    BacktestEngine,
    BacktestJobMetadata,
    BacktestResult,
    Metrics,
    Signal,
    Strategy,
    Trade,
)

__all__ = [
    "BacktestEngine",
    "BacktestJobMetadata",
    "BacktestResult",
    "Metrics",
    "Signal",
    "Strategy",
    "Trade",
]
