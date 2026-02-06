"""Return resampling utilities for equity curve stress paths."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence


@dataclass
class MonteCarloResult:
    trajectories: List[List[float]]
    percentiles: dict[str, List[float]]


class _LCG:
    def __init__(self, seed: int) -> None:
        self._state = seed & 0xFFFFFFFF

    def next_u32(self) -> int:
        self._state = (1664525 * self._state + 1013904223) & 0xFFFFFFFF
        return self._state

    def next_index(self, mod: int) -> int:
        if mod <= 0:
            return 0
        return self.next_u32() % mod


def resample_paths(
    returns: Sequence[float],
    *,
    runs: int = 100,
    seed: int = 0,
    starting_value: float = 1.0,
) -> MonteCarloResult:
    if not returns:
        return MonteCarloResult(trajectories=[], percentiles={"p5": [], "p50": [], "p95": []})
    rng = _LCG(seed)
    paths: List[List[float]] = []
    for _ in range(runs):
        equity = [float(starting_value)]
        for _ in range(len(returns)):
            idx = rng.next_index(len(returns))
            r = returns[idx]
            equity.append(equity[-1] * (1.0 + r))
        paths.append(equity)
    percentiles = _compute_percentiles(paths)
    return MonteCarloResult(trajectories=paths, percentiles=percentiles)


def _compute_percentiles(paths: List[List[float]]) -> dict[str, List[float]]:
    if not paths:
        return {"p5": [], "p50": [], "p95": []}
    length = min(len(p) for p in paths)
    p5: List[float] = []
    p50: List[float] = []
    p95: List[float] = []
    for i in range(length):
        values = sorted(p[i] for p in paths)
        p5.append(_percentile(values, 5))
        p50.append(_percentile(values, 50))
        p95.append(_percentile(values, 95))
    return {"p5": p5, "p50": p50, "p95": p95}


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    k = (len(values) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(values) - 1)
    if f == c:
        return values[f]
    d0 = values[f] * (c - k)
    d1 = values[c] * (k - f)
    return d0 + d1


__all__ = ["MonteCarloResult", "resample_paths"]
