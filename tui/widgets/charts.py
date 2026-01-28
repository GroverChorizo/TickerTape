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
    """Minimal table renderer with numeric formatting and heat indicators.

    update_table supports:
    - headers: list of column headers
    - rows: list of rows where each row is a sequence of values
    - numeric_cols: optional sequence of column indices that should be formatted as numbers
    - heat_cols: optional mapping of column index -> max_value for rendering heat bars
    - width: width for heat bars
    """

    def update_table(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence],
        *,
        numeric_cols: Sequence[int] | None = None,
        heat_cols: dict[int, float] | None = None,
        heat_width: int = 6,
    ) -> None:
        lines: List[str] = []
        if headers:
            lines.append(" | ".join(headers))
        numeric_cols = list(numeric_cols or [])
        heat_cols = dict(heat_cols or {})
        for row in rows:
            formatted_cells: List[str] = []
            for i, cell in enumerate(row):
                if i in numeric_cols:
                    # format numeric with sign for floats
                    try:
                        v = float(cell)
                        cell_str = f"{v:+.4f}" if abs(v) >= 1 else f"{v:+.6f}"
                    except Exception:
                        cell_str = str(cell)
                else:
                    cell_str = str(cell)
                # append heat bar if requested
                if i in heat_cols:
                    try:
                        val = abs(float(row[i]))
                    except Exception:
                        val = 0.0
                    max_val = float(heat_cols.get(i) or 1.0)
                    bar = heat_bar(val, max_val, width=heat_width)
                    cell_str = f"{cell_str} {bar}"
                formatted_cells.append(cell_str)
            lines.append(" | ".join(formatted_cells))
        if not lines:
            lines.append("No data.")
        self.update(Text("\n".join(lines)))
