"""Shared chart widgets for panels."""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

from rich.text import Text
from textual.widgets import Static

from tui.render.sparkline import heat_bar, sparkline


class SparklineWidget(Static):
    """Compact sparkline widget."""

    def update_series(
        self, values: Iterable[float], *, label: str | None = None
    ) -> None:
        line = sparkline(list(values), width=24)
        text = f"{label}: {line}" if label else line
        self.update(Text(text))


class HeatmapWidget(Static):
    """Compact heatmap list widget."""

    def update_pairs(
        self, pairs: Sequence[Tuple[str, float]], *, width: int = 16
    ) -> None:
        if not pairs:
            self.update(Text("No data."))
            return
        max_val = max(value for _, value in pairs) or 1.0
        lines: List[str] = []
        for label, value in pairs:
            bar = heat_bar(value, max_val, width=width)
            lines.append(f"{label:<6} {bar} {value:,.2f}")
        self.update(Text("\n".join(lines)))


class BarChartWidget(Static):
    """Simple horizontal bar chart."""

    def update_bars(
        self, bars: Sequence[Tuple[str, float]], *, width: int = 12
    ) -> None:
        if not bars:
            self.update(Text("No data."))
            return
        max_val = max(abs(value) for _, value in bars) or 1.0
        lines: List[str] = []
        for label, value in bars:
            bar = heat_bar(abs(value), max_val, width=width)
            lines.append(f"{label:<6} {bar} {value:,.2f}")
        self.update(Text("\n".join(lines)))


class TableWidget(Static):
    """Minimal table renderer."""

    def update_table(
        self, headers: Sequence[str], rows: Sequence[Sequence[str]]
    ) -> None:
        lines: List[str] = []
        if headers:
            lines.append(" | ".join(headers))
        for row in rows:
            lines.append(" | ".join(str(cell) for cell in row))
        if not lines:
            lines.append("No data.")
        self.update(Text("\n".join(lines)))
