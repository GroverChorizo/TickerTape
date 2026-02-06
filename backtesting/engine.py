"""Deterministic backtest engine for price-series strategies."""

from __future__ import annotations

from typing import List, Sequence
import math
import time

from tickertape.core.backtesting import BacktestResult, Trade


def run_backtest(
    prices: Sequence[float],
    signals: Sequence[int],
    *,
    starting_cash: float = 10_000.0,
    fee_bps: float = 0.0,
    slippage_bps: float = 0.0,
    allow_short: bool = True,
    run_id: str | None = None,
) -> BacktestResult:
    if len(prices) != len(signals):
        raise ValueError("prices and signals must have the same length")
    if not prices:
        return BacktestResult(run_id=run_id or "empty", timestamps=[], equity_curve=[], metrics={})

    cash = float(starting_cash)
    position_qty = 0.0
    equity_curve: List[float] = []
    timestamps: List[int] = []
    trades: List[Trade] = []

    for idx, (price, signal) in enumerate(zip(prices, signals)):
        if price is None:
            continue
        px = float(price)
        if signal not in (-1, 0, 1):
            raise ValueError("signals must be -1, 0, or 1")
        if signal == -1 and not allow_short:
            signal = 0

        target_qty = 0.0
        if signal != 0 and px > 0:
            target_qty = (cash / px) * signal

        if not math.isclose(target_qty, position_qty, rel_tol=1e-9, abs_tol=1e-9):
            delta_qty = target_qty - position_qty
            side = "buy" if delta_qty > 0 else "sell"
            trade_px = _apply_slippage(px, slippage_bps, side)
            notional = abs(delta_qty) * trade_px
            fee = notional * (fee_bps / 10_000.0)
            cash -= delta_qty * trade_px
            cash -= fee
            position_qty = target_qty
            trades.append(
                Trade(
                    ts_ms=_ts_from_index(idx),
                    symbol="",
                    side="long" if delta_qty > 0 else "short",
                    qty=abs(delta_qty),
                    price=trade_px,
                    fees=fee,
                    pnl=None,
                )
            )

        equity = cash + (position_qty * px)
        equity_curve.append(equity)
        timestamps.append(_ts_from_index(idx))

    metrics = _compute_metrics(equity_curve)
    return BacktestResult(
        run_id=run_id or f"bt_{int(time.time() * 1000)}",
        timestamps=timestamps,
        equity_curve=equity_curve,
        metrics=metrics,
        trades=trades,
    )


def _apply_slippage(price: float, slippage_bps: float, side: str) -> float:
    if slippage_bps <= 0:
        return price
    adj = price * (slippage_bps / 10_000.0)
    return price + adj if side == "buy" else price - adj


def _compute_metrics(equity: Sequence[float]) -> dict[str, float]:
    if not equity:
        return {}
    returns = _returns(equity)
    sharpe = _sharpe(returns)
    sortino = _sortino(returns)
    max_dd = _max_drawdown(equity)
    return {
        "start": float(equity[0]),
        "end": float(equity[-1]),
        "return": float(equity[-1] - equity[0]),
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_dd,
    }


def _returns(equity: Sequence[float]) -> List[float]:
    out: List[float] = []
    for i in range(1, len(equity)):
        prev = equity[i - 1]
        if prev == 0:
            out.append(0.0)
        else:
            out.append((equity[i] - prev) / prev)
    return out


def _sharpe(returns: Sequence[float]) -> float:
    if not returns:
        return 0.0
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / max(len(returns) - 1, 1)
    std = math.sqrt(var)
    if std == 0:
        return 0.0
    return mean / std


def _sortino(returns: Sequence[float]) -> float:
    if not returns:
        return 0.0
    mean = sum(returns) / len(returns)
    downside = [r for r in returns if r < 0]
    if not downside:
        return 0.0
    var = sum((r) ** 2 for r in downside) / max(len(downside) - 1, 1)
    std = math.sqrt(var)
    if std == 0:
        return 0.0
    return mean / std


def _max_drawdown(equity: Sequence[float]) -> float:
    peak = -float("inf")
    max_dd = 0.0
    for value in equity:
        peak = max(peak, value)
        if peak > 0:
            dd = (peak - value) / peak
            max_dd = max(max_dd, dd)
    return max_dd


def _ts_from_index(idx: int) -> int:
    return idx


__all__ = ["run_backtest"]
