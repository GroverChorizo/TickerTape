"""Orderbook panel for Day Trader."""

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


class OrderbookPanel(PanelBase):
    def __init__(self) -> None:
        super().__init__(panel_id="orderbook", title="Orderbook")
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
            self._render_empty("No orderbook data yet.")
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
            muted_line("Loading orderbook...", self.palette),
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
        orderbook = payload.get("orderbook") if isinstance(payload, dict) else None
        if not isinstance(orderbook, dict):
            self._render_empty("No orderbook data.")
            return
        bids = orderbook.get("bids") if isinstance(orderbook.get("bids"), list) else []
        asks = orderbook.get("asks") if isinstance(orderbook.get("asks"), list) else []
        if not bids and not asks:
            self._render_empty("No orderbook levels.")
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
        ]
        lines.extend(self._best_line(bids, asks))
        lines.append(self._header_line())
        for idx in range(10):
            bid = bids[idx] if idx < len(bids) else {}
            ask = asks[idx] if idx < len(asks) else {}
            lines.append(self._row_line(bid, ask))
        self.update_text(build_text(lines))

    def _best_line(self, bids: list, asks: list) -> List[Any]:
        best_bid = _level(bids, 0)
        best_ask = _level(asks, 0)
        bid_px = best_bid.get("price") if best_bid else None
        ask_px = best_ask.get("price") if best_ask else None
        mid = None
        spread = None
        if bid_px is not None and ask_px is not None:
            try:
                mid = (float(bid_px) + float(ask_px)) / 2.0
                spread = float(ask_px) - float(bid_px)
            except Exception:
                mid = None
        summary = Text()
        summary.append("Best Bid: ", style=self.palette.text.primary)
        summary.append(_fmt_price(bid_px), style=self.palette.accent.green)
        summary.append(" | Best Ask: ", style=self.palette.text.primary)
        summary.append(_fmt_price(ask_px), style=self.palette.accent.red)
        summary.append(" | Mid: ", style=self.palette.text.primary)
        summary.append(_fmt_price(mid), style=self.palette.text.primary)
        summary.append(" | Spread: ", style=self.palette.text.primary)
        summary.append(_fmt_price(spread), style=self.palette.text.primary)
        return [summary]

    def _header_line(self) -> Text:
        header = Text()
        header.append("Bid Size", style=f"bold {self.palette.accent.green}")
        header.append(" | ")
        header.append("Bid Price", style=f"bold {self.palette.accent.green}")
        header.append(" | ")
        header.append("Ask Price", style=f"bold {self.palette.accent.red}")
        header.append(" | ")
        header.append("Ask Size", style=f"bold {self.palette.accent.red}")
        return header

    def _row_line(self, bid: Any, ask: Any) -> Text:
        bid_size = _fmt_number(_get(bid, "size"))
        bid_price = _fmt_price(_get(bid, "price"))
        ask_price = _fmt_price(_get(ask, "price"))
        ask_size = _fmt_number(_get(ask, "size"))
        row = Text()
        row.append(f"{bid_size:>8}", style=numeric_style_for(_get(bid, "size"), self.palette))
        row.append(" | ")
        row.append(f"{bid_price:>9}", style=self.palette.accent.green)
        row.append(" | ")
        row.append(f"{ask_price:>9}", style=self.palette.accent.red)
        row.append(" | ")
        row.append(f"{ask_size:>8}", style=numeric_style_for(_get(ask, "size"), self.palette))
        return row


def _level(levels: list, idx: int) -> dict:
    if not isinstance(levels, list) or idx >= len(levels):
        return {}
    level = levels[idx]
    if isinstance(level, dict):
        return level
    if isinstance(level, (list, tuple)) and len(level) >= 2:
        return {"price": level[0], "size": level[1]}
    return {}


def _get(level: Any, key: str) -> Any:
    if isinstance(level, dict):
        return level.get(key)
    return None


def _fmt_price(value: Any) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if abs(v) >= 1000:
        return f"{v:,.2f}"
    return f"{v:,.4f}"


def _fmt_number(value: Any) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    return f"{v:.3f}"
