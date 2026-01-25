"""Market data panel for DayTrader."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional

from ..feeds.base import FeedResult
from tui.render.palette import build_text, error_footer, format_last_good, heading_line, muted_line, status_line
from .panel_base import PanelBase


class MarketDataPanel(PanelBase):
    def __init__(self) -> None:
        super().__init__(panel_id="positions", title="Market Data")
        self.feed_result = FeedResult(status="loading")

    def update_feed(self, result: FeedResult) -> None:
        self.feed_result = result
        self.refresh_panel()

    def refresh_panel(self) -> None:
        status = self.feed_result.status
        if status == "loading":
            self.render_loading()
            return
        if status in {"error", "disconnected"} and not self.feed_result.data:
            self.render_error(
                self.feed_result.error or "Unknown error",
                hint="Check API base URL or endpoint availability.",
                updated_ts_ms=self.feed_result.updated_ts_ms,
            )
            return
        if status == "empty" and not self.feed_result.data:
            self.render_empty("No data yet.")
            return
        self.render_data(
            self.feed_result.data,
            status=status,
            is_lkg=self.feed_result.is_lkg,
            updated_ts_ms=self.feed_result.updated_ts_ms,
        )

    def render_loading(self) -> None:
        self.set_status_class("loading")
        lines = [
            status_line("loading", self.palette),
            muted_line("Loading market data...", self.palette),
        ]
        self.update_text(build_text(lines))

    def render_empty(self, reason: str) -> None:
        self.set_status_class("empty")
        lines = [
            status_line("empty", self.palette),
            muted_line(f"No market data. {reason}", self.palette),
        ]
        self.update_text(build_text(lines))

    def render_error(self, error: str, hint: str, updated_ts_ms: int | None) -> None:
        self.set_status_class("error")
        lines = error_footer(error, updated_ts_ms, backoff_note="feed-managed", palette=self.palette)
        lines.append((f"Hint: {hint}", self.palette.text.muted))
        self.update_text(build_text(lines))

    def render_data(
        self,
        payload: dict,
        status: str = "ok",
        is_lkg: bool = False,
        updated_ts_ms: int | None = None,
    ) -> None:
        if not isinstance(payload, dict):
            self.set_status_class("empty")
            lines = [
                status_line("empty", self.palette),
                muted_line("No market data available.", self.palette),
            ]
            self.update_text(build_text(lines))
            return
        styled_lines: List[tuple[str, str | None]] = []
        self.set_status_class("disconnected" if status == "disconnected" else "ok")
        styled_lines.append(status_line("disconnected" if status == "disconnected" else "ok", self.palette))
        if status == "disconnected" or is_lkg:
            styled_lines.append(muted_line(f"Showing last known data. Last good: {format_last_good(updated_ts_ms)}", self.palette))
        selected_coin = payload.get("selected_coin") or "BTC"
        styled_lines.append((f"Selected coin: {selected_coin}", self.palette.text.primary))
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            styled_lines.append(("Partial errors: " + "; ".join(str(e) for e in errors[:3]), self.palette.accent.orange))

        self._render_top_coins(styled_lines, payload.get("top_coins"))
        self._render_quick_price(styled_lines, payload.get("quick"))
        self._render_orderbook(styled_lines, payload.get("orderbook"))
        self._render_candles(styled_lines, "1h", payload.get("candles_1h"))
        self._render_candles(styled_lines, "1m", payload.get("candles_1m"))
        self.update_text(build_text(styled_lines))

    def _render_top_coins(self, lines: List[tuple[str, str | None]], top_coins: Any) -> None:
        lines.append(("", None))
        lines.append(heading_line("Top Coins", self.palette))
        if not isinstance(top_coins, list) or not top_coins:
            lines.append(muted_line("No top coin data.", self.palette))
            return
        lines.append(("Symbol | Last | Mid | Funding | OI", self.palette.accent.cyan))
        for entry in top_coins[:10]:
            if not isinstance(entry, dict):
                continue
            symbol = entry.get("symbol") or "?"
            last = self._fmt_num(entry.get("last"))
            mid = self._fmt_num(entry.get("mid"))
            funding = self._fmt_num(entry.get("funding"))
            oi = self._fmt_num(entry.get("open_interest"))
            lines.append((f"{symbol} | {last} | {mid} | {funding} | {oi}", self.palette.text.primary))

    def _render_quick_price(self, lines: List[tuple[str, str | None]], quick: Any) -> None:
        lines.append(("", None))
        lines.append(heading_line("Quick Price", self.palette))
        if not isinstance(quick, dict):
            lines.append(muted_line("No quick price data.", self.palette))
            return
        bid = self._fmt_num(quick.get("best_bid"))
        ask = self._fmt_num(quick.get("best_ask"))
        mid = self._fmt_num(quick.get("mid"))
        spread = self._fmt_num(quick.get("spread"))
        ts = self._fmt_ts(quick.get("timestamp_ms"))
        lines.append((f"Bid: {bid} | Ask: {ask} | Mid: {mid} | Spread: {spread}", self.palette.text.primary))
        lines.append(muted_line(f"Updated: {ts}", self.palette))

    def _render_orderbook(self, lines: List[tuple[str, str | None]], orderbook: Any) -> None:
        lines.append(("", None))
        lines.append(heading_line("Orderbook (Top 10)", self.palette))
        if not isinstance(orderbook, dict):
            lines.append(muted_line("No orderbook data.", self.palette))
            return
        bids = orderbook.get("bids") if isinstance(orderbook.get("bids"), list) else []
        asks = orderbook.get("asks") if isinstance(orderbook.get("asks"), list) else []
        if not bids and not asks:
            lines.append(muted_line("No orderbook levels.", self.palette))
            return
        lines.append(("Bid Size | Bid Price | Ask Price | Ask Size", self.palette.accent.cyan))
        depth = max(len(bids), len(asks))
        for i in range(min(depth, 10)):
            bid = bids[i] if i < len(bids) else {}
            ask = asks[i] if i < len(asks) else {}
            bid_size = self._fmt_num(bid.get("size")) if isinstance(bid, dict) else ""
            bid_price = self._fmt_num(bid.get("price")) if isinstance(bid, dict) else ""
            ask_price = self._fmt_num(ask.get("price")) if isinstance(ask, dict) else ""
            ask_size = self._fmt_num(ask.get("size")) if isinstance(ask, dict) else ""
            lines.append((f"{bid_size} | {bid_price} | {ask_price} | {ask_size}", self.palette.text.primary))

    def _render_candles(self, lines: List[tuple[str, str | None]], label: str, candles: Any) -> None:
        lines.append(("", None))
        lines.append(heading_line(f"Candles ({label})", self.palette))
        if not isinstance(candles, list) or not candles:
            lines.append(muted_line("No candle data.", self.palette))
            return
        lines.append(("Time | Open | High | Low | Close | Vol", self.palette.accent.cyan))
        for entry in candles[-10:]:
            if not isinstance(entry, dict):
                continue
            ts = self._fmt_ts(entry.get("timestamp_ms"))
            open_v = self._fmt_num(entry.get("open"))
            high = self._fmt_num(entry.get("high"))
            low = self._fmt_num(entry.get("low"))
            close = self._fmt_num(entry.get("close"))
            vol = self._fmt_num(entry.get("volume"))
            lines.append((f"{ts} | {open_v} | {high} | {low} | {close} | {vol}", self.palette.text.primary))

    @staticmethod
    def _fmt_num(value: Optional[float]) -> str:
        if value is None:
            return "n/a"
        if isinstance(value, (int, float)):
            return f"{value:.4f}" if abs(value) < 1000 else f"{value:.2f}"
        return str(value)

    @staticmethod
    def _fmt_ts(ts_ms: Any) -> str:
        if not ts_ms:
            return "unknown"
        try:
            ts_int = int(ts_ms)
        except (TypeError, ValueError):
            return "unknown"
        dt = datetime.fromtimestamp(ts_int / 1000, tz=timezone.utc)
        return dt.strftime("%m/%d %H:%M")
