"""Pure analytics for the Command Center.

No I/O and no global state — every function takes plain numbers and returns
plain numbers, so the math is deterministic and unit-testable without the TUI,
the network, or any data store. Screens feed it the keyless market data they
already have (candles, the metaAndAssetCtxs snapshot) and render the result.
"""

from __future__ import annotations

from math import sqrt
from typing import Dict, List, Optional, Sequence, Tuple

Number = float


def pct_returns(prices: Sequence[float]) -> List[float]:
    """Simple period-over-period returns. Skips non-positive denominators."""
    out: List[float] = []
    for prev, cur in zip(prices, prices[1:]):
        if prev:
            out.append((cur - prev) / prev)
    return out


def mean(xs: Sequence[float]) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def stdev(xs: Sequence[float]) -> float:
    """Population standard deviation (0.0 for <2 points)."""
    xs = list(xs)
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def pearson(a: Sequence[float], b: Sequence[float]) -> Optional[float]:
    """Pearson correlation of two equal-length series; None if undefined."""
    a, b = list(a), list(b)
    n = min(len(a), len(b))
    if n < 2:
        return None
    a, b = a[-n:], b[-n:]
    ma, mb = mean(a), mean(b)
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    if va <= 0 or vb <= 0:
        return None
    return cov / sqrt(va * vb)


def correlation_matrix(
    closes_by_symbol: Dict[str, Sequence[float]],
) -> Tuple[List[str], List[List[Optional[float]]]]:
    """Return (symbols, matrix) of return correlations between each pair.

    Correlations are computed on returns (not raw prices) over the overlapping
    window. Diagonal is 1.0; undefined pairs are None.
    """
    symbols = sorted(closes_by_symbol)
    returns = {s: pct_returns(closes_by_symbol[s]) for s in symbols}
    matrix: List[List[Optional[float]]] = []
    for a in symbols:
        row: List[Optional[float]] = []
        for b in symbols:
            row.append(1.0 if a == b else pearson(returns[a], returns[b]))
        matrix.append(row)
    return symbols, matrix


def realized_vol(returns: Sequence[float], periods_per_year: int = 0) -> float:
    """Std-dev of returns, optionally annualized by sqrt(periods_per_year)."""
    sd = stdev(returns)
    if periods_per_year > 0:
        sd *= sqrt(periods_per_year)
    return sd


def percentile_rank(value: float, history: Sequence[float]) -> float:
    """Fraction of ``history`` <= ``value`` (0.0–1.0). 0.5 if history empty."""
    hist = list(history)
    if not hist:
        return 0.5
    return sum(1 for h in hist if h <= value) / len(hist)


def regime(closes: Sequence[float], *, vol_window: int = 14) -> Dict[str, object]:
    """Classify trend + volatility regime from a close series.

    - trend: sign of (last close - SMA) → up / down / flat
    - vol_state: current rolling vol vs its own history percentile → low/normal/high
    Returns a dict with raw numbers too, so the panel can show context.
    """
    closes = [float(c) for c in closes if c is not None]
    if len(closes) < 3:
        return {"trend": "n/a", "vol_state": "n/a", "vol": 0.0, "vol_pct": 0.5, "sma": 0.0}

    sma = mean(closes)
    last = closes[-1]
    drift = (last - sma) / sma if sma else 0.0
    if drift > 0.005:
        trend = "up"
    elif drift < -0.005:
        trend = "down"
    else:
        trend = "flat"

    rets = pct_returns(closes)
    cur_vol = realized_vol(rets[-vol_window:]) if len(rets) >= 2 else 0.0
    # Rolling-vol history for a percentile read.
    hist: List[float] = []
    if len(rets) > vol_window:
        for i in range(vol_window, len(rets) + 1):
            hist.append(realized_vol(rets[i - vol_window : i]))
    pct = percentile_rank(cur_vol, hist) if hist else 0.5
    if pct >= 0.8:
        vol_state = "high"
    elif pct <= 0.2:
        vol_state = "low"
    else:
        vol_state = "normal"

    return {
        "trend": trend,
        "vol_state": vol_state,
        "vol": cur_vol,
        "vol_pct": pct,
        "sma": sma,
        "drift": drift,
    }


def _to_float(v: object) -> Optional[float]:
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def funding_extremes(
    rows: Sequence[Dict[str, object]], n: int = 5
) -> Dict[str, List[Tuple[str, float]]]:
    """Most-positive and most-negative funding from snapshot rows.

    Each row is a market-snapshot record ({"symbol", "funding", ...}).
    """
    pairs: List[Tuple[str, float]] = []
    for r in rows:
        sym = str(r.get("symbol") or "?")
        f = _to_float(r.get("funding"))
        if f is not None:
            pairs.append((sym, f))
    pairs.sort(key=lambda p: p[1])
    return {
        "most_negative": pairs[:n],
        "most_positive": list(reversed(pairs[-n:])),
    }


def oi_leaders(rows: Sequence[Dict[str, object]], n: int = 5) -> List[Tuple[str, float]]:
    """Top markets by open interest from snapshot rows."""
    pairs: List[Tuple[str, float]] = []
    for r in rows:
        sym = str(r.get("symbol") or "?")
        oi = _to_float(r.get("open_interest"))
        if oi is not None:
            pairs.append((sym, oi))
    pairs.sort(key=lambda p: p[1], reverse=True)
    return pairs[:n]
