"""Strategy signal functions for bots.

Each strategy is a pure function over a closed-bar OHLCV frame (tz-aware UTC
index from data_loader.loader.load): same bars in → same answer out. That
determinism is what makes the G3 shadow-vs-backtest replay diff possible.

Only desired position is computed here ( +1 long / -1 short / 0 flat ).
Order events, state, and the kill-switch live in runner.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

import pandas as pd


@dataclass(frozen=True)
class PositionView:
    """Desired position at the last closed bar of the frame."""
    position: int                    # +1 long, -1 short, 0 flat
    bar_ts_ms: int                   # open time of that closed bar (epoch ms UTC)
    bar_close: float
    meta: Dict[str, float] = field(default_factory=dict)


class StrategyError(Exception):
    """Insufficient or unusable input — bot reports an error event, never guesses."""


def _wilder_atr(high, low, close, period: int):
    import numpy as np

    pc = np.roll(close, 1)
    pc[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - pc), np.abs(low - pc)))
    out = np.full(len(close), np.nan)
    out[period - 1] = tr[:period].mean()
    for i in range(period, len(close)):
        out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def _ema(arr, period: int):
    import numpy as np

    out = np.full(len(arr), np.nan)
    k = 2 / (period + 1)
    out[period - 1] = arr[:period].mean()
    for i in range(period, len(arr)):
        out[i] = arr[i] * k + out[i - 1] * (1 - k)
    return out


# VSMA Band parameters — must stay identical to the StratSearch alpha/beta
# runs (StratSearch/beta/vsma_band_beta.py) or the shadow tape is no longer
# comparable to those results. BTC 4H alpha: Sharpe 1.194, PF 2.097 (IS,
# pre-gauntlet — treat as triage numbers only).
VSMA_LENGTH = 20
VSMA_ATR_LENGTH = 14
VSMA_REVERSAL_LOOKBACK = 5
VSMA_STOP_ATR_MULT = 1.5
VSMA_RR_TP1 = 2.0


def _vsma_reversal(o, h, lo, c, i: int, direction: str) -> bool:
    """Candlestick reversal at bar i — exact port of beta detect_reversal."""
    if i < VSMA_REVERSAL_LOOKBACK:
        return False
    body = abs(c[i] - o[i])
    prev_body = abs(c[i - 1] - o[i - 1])
    if direction == "long":
        is_bull = c[i] > o[i]
        prev_bear = c[i - 1] < o[i - 1]
        low_wick = min(o[i], c[i]) - lo[i]
        is_hammer = low_wick > body * 1.5
        is_engulf = body > prev_body and c[i] > o[i - 1]
        return is_bull and (is_hammer or is_engulf or prev_bear)
    is_bear = c[i] < o[i]
    prev_bull = c[i - 1] > o[i - 1]
    up_wick = h[i] - max(o[i], c[i])
    is_shoot = up_wick > body * 1.5
    is_engulf = body > prev_body and c[i] < o[i - 1]
    return is_bear and (is_shoot or is_engulf or prev_bull)


def vsma_band_positions(df: pd.DataFrame, *, vsma_length: int = VSMA_LENGTH,
                        atr_length: int = VSMA_ATR_LENGTH):
    """Per-bar desired position (+1/-1/0) from replaying the VSMA rules.

    Single source of truth for the signal core — the shadow bot reads the
    last element, the gauntlet backtests the whole array. Parameter overrides
    exist ONLY for the plateau scan; the bot always runs the canonical values.
    Returns (positions, trend, atr, vsma) numpy arrays aligned to df rows.
    """
    import numpy as np

    if len(df) < 60:
        raise StrategyError(f"need >= 60 closed bars for VSMA warmup, got {len(df)}")
    o = df["open"].astype(float).to_numpy()
    h = df["high"].astype(float).to_numpy()
    lo = df["low"].astype(float).to_numpy()
    c = df["close"].astype(float).to_numpy()

    atr = _wilder_atr(h, lo, c, atr_length)
    vsma = _ema(c, vsma_length)
    slope = np.gradient(vsma)
    with np.errstate(invalid="ignore"):
        trend = np.where((c > vsma) & (slope > 0), 1,
                         np.where((c < vsma) & (slope < 0), -1, 0))

    warmup = max(vsma_length, atr_length) + 10
    positions = np.zeros(len(c), dtype=np.int8)
    pos = 0
    for i in range(warmup, len(c)):
        # manage first, then entries — beta loop does the same per cycle
        if pos == 1 and trend[i] == -1:
            pos = 0
        elif pos == -1 and trend[i] == 1:
            pos = 0
        if pos == 0:
            bull = c[i] > o[i] and c[i - 1] > o[i - 1]
            bear = c[i] < o[i] and c[i - 1] < o[i - 1]
            if trend[i] == 1 and bull and _vsma_reversal(o, h, lo, c, i, "long"):
                pos = 1
            elif trend[i] == -1 and bear and _vsma_reversal(o, h, lo, c, i, "short"):
                pos = -1
        positions[i] = pos
    return positions, trend, atr, vsma


def vsma_band(df: pd.DataFrame) -> PositionView:
    """VSMA Band (StratSearch beta tier) — trend + candle-reversal entries.

    Exact port of the signal core in StratSearch/beta/vsma_band_beta.py:
      * trend = +1 when close > EMA(close, 20) and the EMA slopes up,
        -1 on the inverse, else 0
      * LONG entry: trend +1, two consecutive bull candles, bullish reversal
        pattern (hammer / engulfing / prev-bear)  — SHORT is the mirror
      * exit: trend flips against the position (VSMA_REVERSAL in beta)
    Stop (1.5×ATR14) and TP1 (2R) ride along in meta for the executor;
    intrabar stop/TP fills are execution-level and not simulated here.
    Desired position is derived by replaying these rules over the closed-bar
    frame, so the answer is a pure function of the data (G3 replay-diffable).
    """
    positions, trend, atr, vsma = vsma_band_positions(df)
    c = df["close"].astype(float).to_numpy()
    pos = int(positions[-1])
    entered_last_bar = pos != 0 and len(positions) > 1 and positions[-1] != positions[-2]

    meta = {
        "vsma": round(float(vsma[-1]), 2),
        "atr": round(float(atr[-1]), 2),
        "trend": int(trend[-1]),
    }
    if entered_last_bar:
        stop_dist = VSMA_STOP_ATR_MULT * float(atr[-1])
        meta["stop"] = round(c[-1] - stop_dist if pos == 1 else c[-1] + stop_dist, 2)
        meta["tp1"] = round(
            c[-1] + stop_dist * VSMA_RR_TP1 if pos == 1 else c[-1] - stop_dist * VSMA_RR_TP1, 2)
    return PositionView(
        position=pos,
        bar_ts_ms=int(df.index[-1].value // 1_000_000),
        bar_close=float(c[-1]),
        meta=meta,
    )


def ma20_60_long_short(df: pd.DataFrame) -> PositionView:
    """MA20 vs MA60 crossover, always in the market (long or short).

    Simplest strategy in the registry — the calibration baseline. SMA of
    closes; desired position is the sign of (MA20 - MA60) at the last
    closed bar. Warmup: 60 bars minimum, no exceptions.
    """
    if len(df) < 60:
        raise StrategyError(f"need >= 60 closed bars for MA60, got {len(df)}")
    close = df["close"].astype(float)
    ma20 = close.rolling(20).mean().iloc[-1]
    ma60 = close.rolling(60).mean().iloc[-1]
    pos = 1 if ma20 > ma60 else -1 if ma20 < ma60 else 0
    return PositionView(
        position=pos,
        bar_ts_ms=int(df.index[-1].value // 1_000_000),
        bar_close=float(close.iloc[-1]),
        meta={"ma20": round(float(ma20), 2), "ma60": round(float(ma60), 2)},
    )


STRATEGIES = {
    "ma20_60": ma20_60_long_short,
    "vsma_band": vsma_band,
}
