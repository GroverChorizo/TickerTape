"""Funding rates panel for Day Trader."""

from __future__ import annotations

from typing import Any, List
from datetime import datetime, timezone

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


class FundingRatesPanel(PanelBase):
    def __init__(self) -> None:
        super().__init__(panel_id="funding_rates", title="Funding Rates")
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
            self._render_empty("No funding data yet.")
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
            muted_line("Loading funding rates...", self.palette),
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
        funding = payload.get("funding") if isinstance(payload, dict) else None
        if not isinstance(funding, dict) or not funding:
            self._render_empty("No funding data.")
            return

        rows = _normalize_rows(funding)
        if self._watchlist:
            watch = {w.upper() for w in self._watchlist}
            rows = [row for row in rows if row["symbol"] in watch]
        if not rows:
            rows = _normalize_rows(funding)

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
        for row in rows[:10]:
            lines.append(self._row_line(row))
        self.update_text(build_text(lines))

    def _header_line(self) -> Text:
        header = Text()
        header.append("Coin", style=f"bold {self.palette.accent.cyan}")
        header.append(" | ")
        header.append("Rate", style=f"bold {self.palette.accent.cyan}")
        header.append(" | ")
        header.append("Updated", style=f"bold {self.palette.accent.cyan}")
        return header

    def _row_line(self, row: dict) -> Text:
        symbol = row.get("symbol") or "?"
        rate = row.get("rate")
        ts = row.get("timestamp_ms")
        rate_str = _fmt_rate(rate)
        ts_str = _fmt_ts(ts)
        row_text = Text()
        row_text.append(f"{symbol:<6}", style=f"bold {self.palette.text.primary}")
        row_text.append(" | ")
        row_text.append(f"{rate_str:>9}", style=numeric_style_for(rate, self.palette))
        row_text.append(" | ")
        row_text.append(f"{ts_str:<8}", style=self.palette.text.muted)
        return row_text


def _normalize_rows(funding: dict) -> List[dict]:
    rows: List[dict] = []
    for symbol, data in funding.items():
        sym = str(symbol).upper()
        latest = None
        if isinstance(data, dict):
            latest = data.get("latest") if isinstance(data.get("latest"), dict) else data
        if isinstance(latest, dict):
            rate = (
                latest.get("rate")
                or latest.get("fundingRate")
                or latest.get("funding_rate")
            )
            ts = (
                latest.get("timestamp_ms")
                or latest.get("time")
                or latest.get("timestamp")
            )
        else:
            rate = data
            ts = None
        rows.append({"symbol": sym, "rate": rate, "timestamp_ms": ts})
    return rows


def _fmt_rate(value: Any) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "n/a"
    return f"{v*100:+.4f}%"


def _fmt_ts(value: Any) -> str:
    if not value:
        return "n/a"
    try:
        ts = int(value)
    except (TypeError, ValueError):
        return "n/a"
    if ts < 1_000_000_000_000:
        ts *= 1000
    dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
    return dt.strftime("%H:%M")
