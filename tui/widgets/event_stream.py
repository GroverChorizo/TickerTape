"""Live event stream panel."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ..backend.registry import get_registry
from ..backend.queries import recent_events
from .panel_base import PanelBase


class EventStream(PanelBase):
    def __init__(self) -> None:
        super().__init__(panel_id="event_stream", title="Live Event Stream")

    def refresh_panel(self) -> None:
        registry = get_registry()
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        events = recent_events(registry, "feed=liquidations_events", now_ms - 5 * 60 * 1000)
        if not events:
            self.update_text("No liquidation events available in the last 5 minutes.")
            return
        lines: List[str] = []
        for event in events[-10:]:
            ts = event.get("timestamp_ms") or hint_ts(event)
            symbol = event.get("symbol", "?")
            side = event.get("side", "?")
            size = event.get("size", "?")
            lines.append(f"[{fmt_ts(ts)}] {symbol} {side} size={size}")
        self.update_text("\n".join(lines))


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
