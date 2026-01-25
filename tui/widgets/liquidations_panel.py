"""Liquidations panel: live liquidation stats."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ..feeds.base import FeedResult
from .panel_base import PanelBase


class LiquidationsPanel(PanelBase):
    def __init__(self) -> None:
        super().__init__(panel_id="liquidations", title="Liquidations")
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
            "Loading liquidation stats...",
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
        snapshot = payload.get("snapshot") if isinstance(payload, dict) else None
        if not isinstance(snapshot, dict):
            self.set_status_class("empty")
            lines = [
                self.format_status_line("empty"),
                "No liquidation snapshot data available.",
            ]
            self.update_text(self.join_lines(lines))
            return
        lines: List[str] = []
        self.set_status_class("disconnected" if status == "disconnected" else "ok")
        lines.append(self.format_status_line("disconnected" if status == "disconnected" else "ok"))
        if status == "disconnected" or is_lkg:
            lines.append(f"Showing last known data. Last good: {self.format_last_good(updated_ts_ms)}")
        total = snapshot.get("total_notional")
        count = snapshot.get("count")
        cascade = snapshot.get("cascade_detected")
        velocity = snapshot.get("velocity_score")
        computed = snapshot.get("computed_at_ts_ms") or snapshot.get("timestamp_ms")
        lines.append(f"Total notional: {self._fmt_money(total)}")
        lines.append(f"Count: {count if count is not None else 'n/a'}")
        lines.append(f"Cascade: {'YES' if cascade else 'no'}")
        if velocity is not None:
            lines.append(f"Velocity: {velocity}")
        lines.append(f"Updated: {self._fmt_ts(computed)}")
        top_symbols = snapshot.get("top_symbols", [])
        if isinstance(top_symbols, list) and top_symbols:
            top_fmt = ", ".join(
                f"{item.get('symbol', '?')} {self._fmt_money(item.get('notional'))}" for item in top_symbols[:3]
            )
            lines.append(f"Top symbols: {top_fmt}")
        self.update_text("\n".join(lines))

    @staticmethod
    def _fmt_ts(ts_ms: int | None) -> str:
        if not ts_ms:
            return "unknown"
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

    @staticmethod
    def _fmt_money(value: object) -> str:
        try:
            return f"${float(value):,.0f}"
        except (TypeError, ValueError):
            return "n/a"
