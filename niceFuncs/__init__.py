"""niceFuncs — the only sanctioned metrics/stress calculators.

Shared between the backtest engine and (future) live shadow diffing, per the
backtest contract: every reported number comes from here so backtest and
live can never disagree about arithmetic.

Conventions:
  * 24/7 annualization — crypto has no trading days. bars_per_year is derived
    from the bar interval (4h -> 2,190; 15m -> 35,040).
  * Monte Carlo is permutation WITHOUT replacement (reordering reality, not
    resampling it) — bootstrap-with-replacement caused a real bug here once.
  * Deterministic: same inputs + seed -> same outputs, stdlib RNG only.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Sequence

MS_PER_YEAR = 365 * 24 * 3_600 * 1000


def bars_per_year(timeframe_ms: int) -> float:
    """24/7 annualization factor: how many bars of this size fit in a year."""
    if timeframe_ms <= 0:
        raise ValueError("timeframe_ms must be positive")
    return MS_PER_YEAR / timeframe_ms


def returns_from_equity(equity: Sequence[float]) -> List[float]:
    out: List[float] = []
    for i in range(1, len(equity)):
        prev = equity[i - 1]
        out.append((equity[i] - prev) / prev if prev else 0.0)
    return out


def metrics(equity: Sequence[float], *, timeframe_ms: int) -> Dict[str, float]:
    """Core performance metrics from an equity curve. Label every use IS/WF/OOS
    at the call site — the numbers do not know where the data came from."""
    if len(equity) < 2:
        return {}
    rets = returns_from_equity(equity)
    n = len(rets)
    mean = sum(rets) / n
    var = sum((r - mean) ** 2 for r in rets) / max(n - 1, 1)
    std = math.sqrt(var)
    downside = [r for r in rets if r < 0]
    dvar = sum(r * r for r in downside) / max(len(downside) - 1, 1) if downside else 0.0
    dstd = math.sqrt(dvar)
    ann = math.sqrt(bars_per_year(timeframe_ms))

    peak, max_dd = equity[0], 0.0
    for v in equity:
        peak = max(peak, v)
        if peak > 0:
            max_dd = max(max_dd, (peak - v) / peak)

    return {
        "return_pct": (equity[-1] / equity[0] - 1.0) * 100.0,
        "sharpe_ann": (mean / std * ann) if std else 0.0,
        "sortino_ann": (mean / dstd * ann) if dstd else 0.0,
        "max_drawdown_pct": max_dd * 100.0,
        "bars": float(len(equity)),
        "exposure_years": len(rets) / bars_per_year(timeframe_ms),
    }


def trade_stats(trade_pnls: Sequence[float]) -> Dict[str, float]:
    """Win rate / profit factor from per-trade PnL. n<50 -> treat PF as noise."""
    n = len(trade_pnls)
    if n == 0:
        return {"n_trades": 0.0}
    wins = [p for p in trade_pnls if p > 0]
    losses = [p for p in trade_pnls if p <= 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    return {
        "n_trades": float(n),
        "win_rate_pct": len(wins) / n * 100.0,
        "profit_factor": (gross_win / gross_loss) if gross_loss else float("inf"),
        "avg_trade_pnl": sum(trade_pnls) / n,
    }


@dataclass
class PermutationMCResult:
    runs: int
    seed: int
    max_dd_p5_pct: float
    max_dd_p50_pct: float
    max_dd_p95_pct: float
    observed_final: float
    observed_dd_pct: float
    dds_pct: List[float] = field(default_factory=list, repr=False)


def permutation_mc(
    per_bar_returns: Sequence[float],
    *,
    runs: int = 1000,
    seed: int = 7,
    starting_value: float = 1.0,
) -> PermutationMCResult:
    """Shuffle the OBSERVED returns (no replacement) `runs` times.

    Final equity is order-invariant under permutation (multiplication
    commutes), so the only information here is the DRAWDOWN distribution and
    where the observed path sits inside it. No final-equity percentiles are
    reported — they would all equal the observed final.
    """
    base = list(per_bar_returns)
    if not base:
        raise ValueError("no returns to permute — refuse to fabricate")

    def path_stats(rets: Sequence[float]) -> tuple[float, float]:
        eq, peak, dd = starting_value, starting_value, 0.0
        for r in rets:
            eq *= 1.0 + r
            peak = max(peak, eq)
            if peak > 0:
                dd = max(dd, (peak - eq) / peak)
        return eq, dd

    observed_final, observed_dd = path_stats(base)

    dds: List[float] = []
    for k in range(runs):
        rng = random.Random(seed + k)
        sample = base[:]
        rng.shuffle(sample)            # permutation, never resampling
        _, d = path_stats(sample)
        dds.append(d)

    dds_sorted = sorted(dds)
    return PermutationMCResult(
        runs=runs,
        seed=seed,
        max_dd_p5_pct=_pct(dds_sorted, 5) * 100.0,
        max_dd_p50_pct=_pct(dds_sorted, 50) * 100.0,
        max_dd_p95_pct=_pct(dds_sorted, 95) * 100.0,
        observed_final=observed_final,
        observed_dd_pct=observed_dd * 100.0,
        dds_pct=[d * 100.0 for d in dds],
    )


def unit_backtest(
    opens: Sequence[float],
    positions: Sequence[int],
    *,
    fee_bps: float = 0.0,
    slippage_bps: float = 0.0,
) -> List[float]:
    """Unit-exposure backtest with NEXT-BAR-OPEN fills.

    positions[i] is the exposure decided on bar i's close (+1/-1/0); it is
    filled at bar i+1's open and held until the next change fills. Exposure
    is always exactly 1x equity — no compounding-leverage pathologies (the
    cash-based engine resizes shorts from cash each bar, which explodes; see
    2026-06-11 gauntlet run). Costs: (fee+slippage) bps per unit of exposure
    change, charged at the fill.

    Returns the equity curve sampled at each open from opens[1:], starting
    at 1.0.
    """
    if len(opens) != len(positions):
        raise ValueError("opens and positions must align")
    if len(opens) < 2:
        return [1.0]
    cost_rate = (fee_bps + slippage_bps) / 10_000.0
    equity = [1.0]
    eq = 1.0
    prev_exposure = 0
    for j in range(1, len(opens)):
        exposure = int(positions[j - 1])          # decided at close of j-1
        turnover = abs(exposure - prev_exposure)  # filled at open[j]
        if turnover:
            eq *= 1.0 - cost_rate * turnover
        if j + 1 < len(opens) and exposure != 0 and opens[j] > 0:
            eq *= 1.0 + exposure * (opens[j + 1] / opens[j] - 1.0)
        prev_exposure = exposure
        equity.append(eq)
    return equity


def _pct(sorted_values: List[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    return sorted_values[f] * (c - k) + sorted_values[c] * (k - f)


__all__ = [
    "bars_per_year",
    "metrics",
    "trade_stats",
    "returns_from_equity",
    "unit_backtest",
    "permutation_mc",
    "PermutationMCResult",
]
