"""Whale activity panel."""
from __future__ import annotations

from typing import List

from ..feeds.base import FeedResult
from tui.render.palette import build_text, error_footer, format_last_good, heading_line, muted_line, status_line
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
            status_line("loading", self.palette),
            muted_line("Loading whale trades...", self.palette),
        ]
        self.update_text(build_text(lines))

    def render_empty(self, reason: str) -> None:
        self.set_status_class("empty")
        lines = [
            status_line("empty", self.palette),
            muted_line(f"No data. {reason}", self.palette),
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
        trades = payload.get("trades") if isinstance(payload, dict) else None
        if isinstance(trades, dict):
            trades = trades.get("trades") or trades.get("data") or trades.get("events")
        if not isinstance(trades, list) or not trades:
            self.set_status_class("empty")
            lines = [
                status_line("empty", self.palette),
                muted_line("No whale trade data available.", self.palette),
            ]
            self.update_text(build_text(lines))
            return
        filtered = [t for t in trades if _meets_min_notional(t, self.min_notional)]
        styled_lines: List[tuple[str, str]] = []
        self.set_status_class("disconnected" if status == "disconnected" else "ok")
        styled_lines.append(status_line("disconnected" if status == "disconnected" else "ok", self.palette))
        if status == "disconnected" or is_lkg:
            styled_lines.append(muted_line(f"Showing last known data. Last good: {format_last_good(updated_ts_ms)}", self.palette))
        styled_lines.append(heading_line("Recent whale trades:", self.palette))
        for event in (filtered or trades)[-5:]:
            symbol = event.get("symbol") or event.get("coin") or "?"
            side = event.get("side") or event.get("direction") or "?"
            size = event.get("size") or event.get("amount") or "?"
            price = event.get("price") or "?"
            wallet = event.get("wallet") or event.get("wallet_address") or event.get("address")
            wallet_hint = f" wallet={wallet}" if isinstance(wallet, str) and wallet else ""
            styled_lines.append((f"- {symbol} {side} size={size} price={price}{wallet_hint}", self.palette.accent.cyan))
        self.update_text(build_text(styled_lines))
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
