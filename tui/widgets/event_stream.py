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
            "Loading live events...",
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
        events = payload.get("events") if isinstance(payload, dict) else None
        if not isinstance(events, list) or not events:
            self.set_status_class("empty")
            lines = [
                self.format_status_line("empty"),
                "Waiting for event stream. No recent events available.",
            ]
            self.update_text(self.join_lines(lines))
            return
        lines: List[str] = []
        self.set_status_class("disconnected" if status == "disconnected" else "ok")
        lines.append(self.format_status_line("disconnected" if status == "disconnected" else "ok"))
        if status == "disconnected" or is_lkg:
            lines.append(f"Showing last known data. Last good: {self.format_last_good(updated_ts_ms)}")
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
