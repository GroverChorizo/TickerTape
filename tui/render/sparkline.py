"""Simple text sparkline utilities for panels."""

from __future__ import annotations

from typing import Iterable, List

SPARK_BLOCKS = "▁▂▃▄▅▆▇█"


def sparkline(values: Iterable[float], *, width: int | None = None) -> str:
    series = [v for v in values if v is not None]
    if not series:
        return ""
    if width is not None and width > 0 and len(series) > width:
        series = series[-width:]
    min_v = min(series)
    max_v = max(series)
    if max_v == min_v:
        return SPARK_BLOCKS[0] * len(series)
    span = max_v - min_v
    out: List[str] = []
    for value in series:
        idx = int((value - min_v) / span * (len(SPARK_BLOCKS) - 1))
        out.append(SPARK_BLOCKS[idx])
    return "".join(out)


def heat_bar(value: float, max_value: float, *, width: int = 12) -> str:
    if width <= 0:
        return ""
    if max_value <= 0:
        return "░" * width
    ratio = min(max(value / max_value, 0.0), 1.0)
    filled = int(round(ratio * width))
    return f"{'█' * filled}{'░' * max(width - filled, 0)}"
