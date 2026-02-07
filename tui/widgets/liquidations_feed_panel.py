"""Liquidations feed panel for Day Trader."""

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


class LiquidationsFeedPanel(PanelBase):
    def __init__(self) -> None:
        super().__init__(panel_id="liquidations_feed", title="Liquidations")
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
            self._render_empty("No liquidation data yet.")
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
            muted_line("Loading liquidations...", self.palette),
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
        events = _extract_events(payload)
        if not events:
            self._render_empty("No liquidation events.")
            return
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
        for event in events[:10]:
            lines.append(self._row_line(event))
        self.update_text(build_text(lines))

    def _header_line(self) -> Text:
        header = Text()
        header.append("Time", style=f"bold {self.palette.accent.cyan}")
        header.append(" | ")
        header.append("Coin", style=f"bold {self.palette.accent.cyan}")
        header.append(" | ")
        header.append("Side", style=f"bold {self.palette.accent.cyan}")
        header.append(" | ")
        header.append("Size", style=f"bold {self.palette.accent.cyan}")
        header.append(" | ")
        header.append("Value", style=f"bold {self.palette.accent.cyan}")
        return header

    def _row_line(self, event: dict) -> Text:
        ts = _fmt_ts(event.get("timestamp_ms") or event.get("time"))
        symbol = str(event.get("symbol") or event.get("coin") or "?").upper()
        side = str(event.get("side") or event.get("direction") or "?").lower()
        size = event.get("size") or event.get("amount") or event.get("qty")
        price = event.get("price") or event.get("px")
        notional = event.get("notional_usd") or event.get("value_usd") or event.get("notional")
        if notional is None and size is not None and price is not None:
            try:
                notional = float(size) * float(price)
            except Exception:
                notional = None

        side_color = self.palette.accent.red if side in {"long", "buy", "long_liq"} else self.palette.accent.green
        row = Text()
        row.append(f"{ts:<8}", style=self.palette.text.muted)
        row.append(" | ")
        row.append(f"{symbol:<5}", style=f"bold {self.palette.text.primary}")
        row.append(" | ")
        row.append(f"{side.upper():<6}", style=f"bold {side_color}")
        row.append(" | ")
        row.append(f"{_fmt_number(size):>8}", style=numeric_style_for(size, self.palette))
        row.append(" | ")
        row.append(f"{_fmt_money(notional):>10}", style=numeric_style_for(notional, self.palette))
        return row


def _extract_events(payload: Any) -> List[dict]:
    if not isinstance(payload, dict):
        return []
    events = payload.get("events")
    if isinstance(events, list):
        return [e for e in events if isinstance(e, dict)]
    raw = payload.get("liquidations")
    if isinstance(raw, list):
        return [e for e in raw if isinstance(e, dict)]
    snapshot = payload.get("snapshot")
    if isinstance(snapshot, dict):
        for key in ("liquidations", "events", "data", "rows"):
            raw = snapshot.get(key)
            if isinstance(raw, list):
                return [e for e in raw if isinstance(e, dict)]
    return []


def _fmt_ts(ts_ms: Any) -> str:
    if not ts_ms:
        return "n/a"
    try:
        ts_int = int(ts_ms)
    except (TypeError, ValueError):
        return "n/a"
    if ts_int < 1_000_000_000_000:
        ts_int *= 1000
    dt = datetime.fromtimestamp(ts_int / 1000, tz=timezone.utc)
    return dt.strftime("%H:%M:%S")


def _fmt_number(value: Any) -> str:
    try:
        return f"{float(value):,.3f}"
    except (TypeError, ValueError):
        return "n/a"


def _fmt_money(value: Any) -> str:
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return "n/a"
