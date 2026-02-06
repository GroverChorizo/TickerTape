"""Walk-forward evaluation utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Sequence

from .engine import run_backtest


@dataclass
class WalkForwardWindow:
    train_result: dict
    test_result: dict


@dataclass
class WalkForwardReport:
    windows: List[WalkForwardWindow]
    avg_train_sharpe: float
    avg_test_sharpe: float
    avg_degradation: float


def walk_forward(
    prices: Sequence[float],
    *,
    train_size: int,
    test_size: int,
    strategy_fn: Callable[[Sequence[float]], Sequence[int]],
) -> WalkForwardReport:
    windows: List[WalkForwardWindow] = []
    train_sharpes: List[float] = []
    test_sharpes: List[float] = []
    idx = 0
    while idx + train_size + test_size <= len(prices):
        train_slice = prices[idx : idx + train_size]
        test_slice = prices[idx + train_size : idx + train_size + test_size]
        train_signals = list(strategy_fn(train_slice))
        test_signals = list(strategy_fn(test_slice))
        train_bt = run_backtest(train_slice, train_signals, run_id="train")
        test_bt = run_backtest(test_slice, test_signals, run_id="test")
        train_sharpe = float(train_bt.metrics.get("sharpe", 0.0))
        test_sharpe = float(test_bt.metrics.get("sharpe", 0.0))
        windows.append(
            WalkForwardWindow(
                train_result=train_bt.metrics,
                test_result=test_bt.metrics,
            )
        )
        train_sharpes.append(train_sharpe)
        test_sharpes.append(test_sharpe)
        idx += test_size
    avg_train = _mean(train_sharpes)
    avg_test = _mean(test_sharpes)
    degradation = avg_train - avg_test
    return WalkForwardReport(
        windows=windows,
        avg_train_sharpe=avg_train,
        avg_test_sharpe=avg_test,
        avg_degradation=degradation,
    )


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


__all__ = ["WalkForwardReport", "WalkForwardWindow", "walk_forward"]
