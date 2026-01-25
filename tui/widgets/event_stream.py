"""Live event stream panel."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ..feeds.base import FeedResult
from .panel_base import PanelBase
from .wallet_panel import WalletsDiscovered


class EventStream(PanelBase):
    def __init__(self) -> None:
        super().__init__(panel_id="event_stream", title="Live Event Stream")
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
            self.render_error(self.feed_result.error or "Unknown error", hint="Retrying with backoff.")
            return
        if status == "empty" and not self.feed_result.data:
            self.render_empty("No data yet.")
            return
        self.render_data(self.feed_result.data, status=status, is_lkg=self.feed_result.is_lkg)

    def render_loading(self) -> None:
        self.update_text("Loading live events...")

    def render_empty(self, reason: str) -> None:
        self.update_text(f"No data. {reason}")

    def render_error(self, error: str, hint: str) -> None:
        self.update_text(f"Error: {error}\n{hint}")

    def render_data(self, payload: dict, status: str = "ok", is_lkg: bool = False) -> None:
        events = payload.get("events") if isinstance(payload, dict) else None
        if not isinstance(events, list) or not events:
            self.update_text("Waiting for event stream. No recent events available.")
            return
        lines: List[str] = []
        if status == "disconnected" or is_lkg:
            lines.append("Disconnected — showing last known data.")
        for event in events[-10:]:
            ts = event.get("timestamp_ms") or hint_ts(event)
            symbol = event.get("symbol", "?")
            side = event.get("side", "?")
            size = event.get("size", "?")
            lines.append(f"[{fmt_ts(ts)}] {symbol} {side} size={size}")
        self.update_text("\n".join(lines))
        wallets = _extract_wallets(events)
        if wallets:
            self.post_message(WalletsDiscovered(wallets, source="event_stream"))


def fmt_ts(ts: int | None) -> str:
    if not ts:
        return "unknown"
    dt = datetime.fromtimestamp(int(ts) / 1000, tz=timezone.utc)
    return dt.strftime("%H:%M:%S")


def hint_ts(event: dict) -> int | None:
    if "timestamp" in event:
        try:
            return int(event["timestamp"])
        except Exception:
            return None
    return None


def _extract_wallets(events: List[dict]) -> List[str]:
    wallets: List[str] = []
    for event in events:
        for key in ("wallet", "wallet_address", "address"):
            value = event.get(key)
            if isinstance(value, str) and value:
                wallets.append(value)
    return wallets
