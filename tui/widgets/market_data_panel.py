"""Market data panel for DayTrader."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional

from ..feeds.base import FeedResult
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
            self.format_status_line("loading"),
            "Loading market data...",
        ]
        self.update_text(self.join_lines(lines))

    def render_empty(self, reason: str) -> None:
        self.set_status_class("empty")
        lines = [
            self.format_status_line("empty"),
            f"No market data. {reason}",
        ]
        self.update_text(self.join_lines(lines))

    def render_error(self, error: str, hint: str, updated_ts_ms: int | None) -> None:
        self.set_status_class("error")
        lines = self.format_error_footer(error, updated_ts_ms, backoff_note="feed-managed")
        lines.append(f"Hint: {hint}")
        self.update_text(self.join_lines(lines))

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
                self.format_status_line("empty"),
                "No market data available.",
            ]
            self.update_text(self.join_lines(lines))
            return
        lines: List[str] = []
        self.set_status_class("disconnected" if status == "disconnected" else "ok")
        lines.append(self.format_status_line("disconnected" if status == "disconnected" else "ok"))
        if status == "disconnected" or is_lkg:
            lines.append(f"Showing last known data. Last good: {self.format_last_good(updated_ts_ms)}")
        selected_coin = payload.get("selected_coin") or "BTC"
        lines.append(f"Selected coin: {selected_coin}")
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            lines.append("Partial errors: " + "; ".join(str(e) for e in errors[:3]))

        self._render_top_coins(lines, payload.get("top_coins"))
        self._render_quick_price(lines, payload.get("quick"))
        self._render_orderbook(lines, payload.get("orderbook"))
        self._render_candles(lines, "1h", payload.get("candles_1h"))
        self._render_candles(lines, "1m", payload.get("candles_1m"))
        self.update_text("\n".join(lines))

    def _render_top_coins(self, lines: List[str], top_coins: Any) -> None:
        lines.append("\nTop Coins")
        if not isinstance(top_coins, list) or not top_coins:
            lines.append("No top coin data.")
            return
        lines.append("Symbol | Last | Mid | Funding | OI")
        for entry in top_coins[:10]:
            if not isinstance(entry, dict):
                continue
            symbol = entry.get("symbol") or "?"
            last = self._fmt_num(entry.get("last"))
            mid = self._fmt_num(entry.get("mid"))
            funding = self._fmt_num(entry.get("funding"))
            oi = self._fmt_num(entry.get("open_interest"))
            lines.append(f"{symbol} | {last} | {mid} | {funding} | {oi}")

    def _render_quick_price(self, lines: List[str], quick: Any) -> None:
        lines.append("\nQuick Price")
        if not isinstance(quick, dict):
            lines.append("No quick price data.")
            return
        bid = self._fmt_num(quick.get("best_bid"))
        ask = self._fmt_num(quick.get("best_ask"))
        mid = self._fmt_num(quick.get("mid"))
        spread = self._fmt_num(quick.get("spread"))
        ts = self._fmt_ts(quick.get("timestamp_ms"))
        lines.append(f"Bid: {bid} | Ask: {ask} | Mid: {mid} | Spread: {spread}")
        lines.append(f"Updated: {ts}")

    def _render_orderbook(self, lines: List[str], orderbook: Any) -> None:
        lines.append("\nOrderbook (Top 10)")
        if not isinstance(orderbook, dict):
            lines.append("No orderbook data.")
            return
        bids = orderbook.get("bids") if isinstance(orderbook.get("bids"), list) else []
        asks = orderbook.get("asks") if isinstance(orderbook.get("asks"), list) else []
        if not bids and not asks:
            lines.append("No orderbook levels.")
            return
        lines.append("Bid Size | Bid Price | Ask Price | Ask Size")
        depth = max(len(bids), len(asks))
        for i in range(min(depth, 10)):
            bid = bids[i] if i < len(bids) else {}
            ask = asks[i] if i < len(asks) else {}
            bid_size = self._fmt_num(bid.get("size")) if isinstance(bid, dict) else ""
            bid_price = self._fmt_num(bid.get("price")) if isinstance(bid, dict) else ""
            ask_price = self._fmt_num(ask.get("price")) if isinstance(ask, dict) else ""
            ask_size = self._fmt_num(ask.get("size")) if isinstance(ask, dict) else ""
            lines.append(f"{bid_size} | {bid_price} | {ask_price} | {ask_size}")

    def _render_candles(self, lines: List[str], label: str, candles: Any) -> None:
        lines.append(f"\nCandles ({label})")
        if not isinstance(candles, list) or not candles:
            lines.append("No candle data.")
            return
        lines.append("Time | Open | High | Low | Close | Vol")
        for entry in candles[-10:]:
            if not isinstance(entry, dict):
                continue
            ts = self._fmt_ts(entry.get("timestamp_ms"))
            open_v = self._fmt_num(entry.get("open"))
            high = self._fmt_num(entry.get("high"))
            low = self._fmt_num(entry.get("low"))
            close = self._fmt_num(entry.get("close"))
            vol = self._fmt_num(entry.get("volume"))
            lines.append(f"{ts} | {open_v} | {high} | {low} | {close} | {vol}")

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
