"""Whale activity panel."""
from __future__ import annotations

from typing import List

from ..feeds.base import FeedResult
from .panel_base import PanelBase
from .wallet_panel import WalletsDiscovered


class WhalePanel(PanelBase):
    def __init__(self) -> None:
        super().__init__(panel_id="whales", title="Whale Activity")
        self.feed_result = FeedResult(status="loading")
        self.min_notional = 25_000

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
            "Loading whale trades...",
        ]
        self.update_text(self.join_lines(lines))

    def render_empty(self, reason: str) -> None:
        self.set_status_class("empty")
        lines = [
            self.format_status_line("empty"),
            f"No data. {reason}",
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
        trades = payload.get("trades") if isinstance(payload, dict) else None
        if isinstance(trades, dict):
            trades = trades.get("trades") or trades.get("data") or trades.get("events")
        if not isinstance(trades, list) or not trades:
            self.set_status_class("empty")
            lines = [
                self.format_status_line("empty"),
                "No whale trade data available.",
            ]
            self.update_text(self.join_lines(lines))
            return
        filtered = [t for t in trades if _meets_min_notional(t, self.min_notional)]
        lines: List[str] = []
        self.set_status_class("disconnected" if status == "disconnected" else "ok")
        lines.append(self.format_status_line("disconnected" if status == "disconnected" else "ok"))
        if status == "disconnected" or is_lkg:
            lines.append(f"Showing last known data. Last good: {self.format_last_good(updated_ts_ms)}")
        lines.append("Recent whale trades:")
        for event in (filtered or trades)[-5:]:
            symbol = event.get("symbol") or event.get("coin") or "?"
            side = event.get("side") or event.get("direction") or "?"
            size = event.get("size") or event.get("amount") or "?"
            price = event.get("price") or "?"
            wallet = event.get("wallet") or event.get("wallet_address") or event.get("address")
            wallet_hint = f" wallet={wallet}" if isinstance(wallet, str) and wallet else ""
            lines.append(f"- {symbol} {side} size={size} price={price}{wallet_hint}")
        self.update_text("\n".join(lines))
        wallets = _extract_wallets(trades)
        if wallets:
            self.post_message(WalletsDiscovered(wallets, source="whales"))


def _extract_wallets(events: List[dict]) -> List[str]:
    wallets: List[str] = []
    for event in events:
        for key in ("wallet", "wallet_address", "address"):
            value = event.get(key)
            if isinstance(value, str) and value:
                wallets.append(value)
    return wallets


def _meets_min_notional(event: dict, threshold: float) -> bool:
    size = event.get("size") or event.get("amount")
    price = event.get("price")
    notional = event.get("notional")
    try:
        if notional is not None:
            return float(notional) >= threshold
        if size is not None and price is not None:
            return float(size) * float(price) >= threshold
    except (TypeError, ValueError):
        return False
    return False
