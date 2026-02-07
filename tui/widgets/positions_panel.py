"""Positions/Open Interest panel for Day Trader."""

from __future__ import annotations

from typing import Any, List

from rich.text import Text

from tui.feeds.base import FeedResult, FeedStatus, _as_status
from tui.render.palette import (
    build_text,
    last_updated_line,
    muted_line,
    panel_header,
    numeric_style_for,
)
from .panel_base import PanelBase


class PositionsPanel(PanelBase):
    def __init__(self) -> None:
        super().__init__(panel_id="positions", title="Positions / Flow")
        self.feed_result = FeedResult(status="loading")
        self._watchlist: List[str] = []

    def set_watchlist(self, watchlist: List[str]) -> None:
        self._watchlist = [w.upper() for w in watchlist if w]

    def update_feed(self, result: FeedResult) -> None:
        self.feed_result = result
        self.refresh_panel()

    def refresh_panel(self) -> None:
        status = _as_status(self.feed_result.status)
        if status == FeedStatus.LOADING:
            self._render_loading()
            return
        if status in {FeedStatus.ERROR, FeedStatus.DISCONNECTED} and not self.feed_result.data:
            self._render_error(self.feed_result.error or "Unknown error")
            return
        if status == FeedStatus.EMPTY and not self.feed_result.data:
            self._render_empty("No positions data yet.")
            return
        self._render_data(
            self.feed_result.data,
            status=status,
            updated_ts_ms=self.feed_result.updated_ts_ms,
        )

    def _render_loading(self) -> None:
        self.set_status_class(FeedStatus.LOADING.value)
        lines = [
            panel_header(self.title, FeedStatus.LOADING.value, self.palette),
            last_updated_line(self.feed_result.updated_ts_ms, self.palette),
            muted_line("Loading positions...", self.palette),
        ]
        self.update_text(build_text(lines))

    def _render_empty(self, reason: str) -> None:
        self.set_status_class(FeedStatus.EMPTY.value)
        lines = [
            panel_header(self.title, FeedStatus.EMPTY.value, self.palette),
            last_updated_line(self.feed_result.updated_ts_ms, self.palette),
            muted_line(reason, self.palette),
        ]
        self.update_text(build_text(lines))

    def _render_error(self, error: str) -> None:
        self.set_status_class(FeedStatus.ERROR.value)
        lines = [
            panel_header(self.title, FeedStatus.ERROR.value, self.palette),
            last_updated_line(self.feed_result.updated_ts_ms, self.palette),
            (error, self.palette.text.primary),
        ]
        self.update_text(build_text(lines))

    def _render_data(
        self,
        payload: dict,
        *,
        status: FeedStatus,
        updated_ts_ms: int | None,
    ) -> None:
        top = payload.get("top_coins") if isinstance(payload, dict) else None
        if not isinstance(top, list) or not top:
            self._render_empty("No open interest data.")
            return

        rows = [row for row in top if isinstance(row, dict)]
        if self._watchlist:
            watch = {w.upper() for w in self._watchlist}
            rows = [row for row in rows if str(row.get("symbol") or "").upper() in watch]
        if not rows:
            rows = [row for row in top if isinstance(row, dict)]

        rows = sorted(
            rows,
            key=lambda r: _safe_float(r.get("open_interest") or 0.0),
            reverse=True,
        )[:10]

        status_value = (
            FeedStatus.DISCONNECTED.value
            if status == FeedStatus.DISCONNECTED
            else FeedStatus.OK.value
        )
        self.set_status_class(status_value)
        lines: List[Any] = [
            panel_header(self.title, status_value, self.palette),
            last_updated_line(updated_ts_ms, self.palette),
            self._header_line(),
        ]
        for entry in rows:
            lines.append(self._row_line(entry))
        self.update_text(build_text(lines))

    def _header_line(self) -> Text:
        header = Text()
        header.append("Coin", style=f"bold {self.palette.accent.cyan}")
        header.append(" | ")
        header.append("OI", style=f"bold {self.palette.accent.cyan}")
        header.append(" | ")
        header.append("Funding", style=f"bold {self.palette.accent.cyan}")
        return header

    def _row_line(self, entry: dict) -> Text:
        symbol = str(entry.get("symbol") or "?").upper()
        oi = _fmt_number(entry.get("open_interest"))
        funding = _fmt_funding(entry.get("funding"))
        funding_style = numeric_style_for(entry.get("funding"), self.palette)
        row = Text()
        row.append(f"{symbol:<6}", style=f"bold {self.palette.text.primary}")
        row.append(" | ")
        row.append(f"{oi:>10}", style=self.palette.text.primary)
        row.append(" | ")
        row.append(f"{funding:>9}", style=funding_style)
        return row


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _fmt_number(value: Any) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    return f"{v:.2f}"


def _fmt_funding(value: Any) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "n/a"
    return f"{v*100:+.4f}%"
