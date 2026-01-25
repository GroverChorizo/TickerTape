"""Funding rates panel with explicit missing-data messaging."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ..feeds.base import FeedResult
from .panel_base import PanelBase


class FundingPanel(PanelBase):
    def __init__(self) -> None:
        super().__init__(panel_id="funding", title="Funding")
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
        self.update_text("Loading funding rates...")

    def render_empty(self, reason: str) -> None:
        self.update_text(f"No data. {reason}")

    def render_error(self, error: str, hint: str) -> None:
        self.update_text(f"Error: {error}\n{hint}")

    def render_data(self, payload: dict, status: str = "ok", is_lkg: bool = False) -> None:
        funding = payload.get("funding") if isinstance(payload, dict) else None
        if not isinstance(funding, dict) or not funding:
            self.update_text("No funding data available.")
            return
        lines: List[str] = []
        if status == "disconnected" or is_lkg:
            lines.append("Disconnected — showing last known data.")
        for coin, item in funding.items():
            latest = item.get("latest") if isinstance(item, dict) else None
            history = item.get("history") if isinstance(item, dict) else None
            rate = latest.get("rate") if isinstance(latest, dict) else None
            ts = latest.get("timestamp_ms") if isinstance(latest, dict) else None
            lines.append(f"{coin}: rate={rate if rate is not None else 'n/a'} updated={self._fmt_ts(ts)}")
            if isinstance(history, list) and history:
                recent = ", ".join(
                    f"{entry.get('rate'):.5f}"
                    for entry in history[-5:]
                    if isinstance(entry, dict) and isinstance(entry.get("rate"), (int, float))
                )
                if recent:
                    lines.append(f"  recent: {recent}")
        self.update_text("\n".join(lines))

    @staticmethod
    def _fmt_ts(ts_ms: int | None) -> str:
        if not ts_ms:
            return "unknown"
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
