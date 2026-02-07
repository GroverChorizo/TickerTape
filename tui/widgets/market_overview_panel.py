"""Market overview panel for Day Trader."""

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


class MarketOverviewPanel(PanelBase):
    def __init__(self) -> None:
        super().__init__(panel_id="market_overview", title="Market Overview")
        self.feed_result = FeedResult(status="loading")

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
            self._render_empty("No market data yet.")
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
            muted_line("Loading top coins...", self.palette),
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
            self._render_empty("No top coin data.")
            return
        self.set_status_class(
            FeedStatus.DISCONNECTED.value
            if status == FeedStatus.DISCONNECTED
            else FeedStatus.OK.value
        )
        lines: List[Any] = [
            panel_header(
                self.title,
                FeedStatus.DISCONNECTED.value
                if status == FeedStatus.DISCONNECTED
                else FeedStatus.OK.value,
                self.palette,
            ),
            last_updated_line(updated_ts_ms, self.palette),
        ]
        lines.append(self._header_line())
        for entry in top[:10]:
            if not isinstance(entry, dict):
                continue
            lines.append(self._row_line(entry))
        self.update_text(build_text(lines))

    def _header_line(self) -> Text:
        header = Text()
        header.append("Coin", style=f"bold {self.palette.accent.cyan}")
        header.append(" | ")
        header.append("Price", style=f"bold {self.palette.accent.cyan}")
        header.append(" | ")
        header.append("Funding", style=f"bold {self.palette.accent.cyan}")
        header.append(" | ")
        header.append("Open Int", style=f"bold {self.palette.accent.cyan}")
        return header

    def _row_line(self, entry: dict) -> Text:
        symbol = str(entry.get("symbol") or "?").upper()
        price = _fmt_price(entry.get("last") or entry.get("price"))
        funding = _fmt_funding(entry.get("funding"))
        oi = _fmt_number(entry.get("open_interest"))
        funding_style = numeric_style_for(entry.get("funding"), self.palette)

        row = Text()
        row.append(f"{symbol:<6}", style=f"bold {self.palette.text.primary}")
        row.append(" | ")
        row.append(f"{price:>10}", style=self.palette.text.primary)
        row.append(" | ")
        row.append(f"{funding:>8}", style=funding_style)
        row.append(" | ")
        row.append(f"{oi:>9}", style=self.palette.text.primary)
        return row


def _fmt_price(value: Any) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if abs(v) >= 1000:
        return f"{v:,.2f}"
    return f"{v:,.4f}"


def _fmt_funding(value: Any) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "n/a"
    pct = v * 100.0
    return f"{pct:+.4f}%"


def _fmt_number(value: Any) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    return f"{v:.2f}"
