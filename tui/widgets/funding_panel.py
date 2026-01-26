"""Funding rates panel with explicit missing-data messaging."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ..feeds.base import FeedResult
from tui.render.palette import build_text, format_last_good, last_updated_line, muted_line, panel_header
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
            panel_header(self.title, "loading", self.palette),
            last_updated_line(self.feed_result.updated_ts_ms, self.palette),
            muted_line("Loading funding rates...", self.palette),
        ]
        self.update_text(build_text(lines))

    def render_empty(self, reason: str) -> None:
        self.set_status_class("empty")
        lines = [
            panel_header(self.title, "empty", self.palette),
            last_updated_line(self.feed_result.updated_ts_ms, self.palette),
            muted_line(f"No data. {reason}", self.palette),
        ]
        self.update_text(build_text(lines))

    def render_error(self, error: str, hint: str, updated_ts_ms: int | None) -> None:
        self.set_status_class("error")
        lines = [
            panel_header(self.title, "error", self.palette),
            last_updated_line(updated_ts_ms, self.palette),
            (error, self.palette.text.primary),
            (f"Hint: {hint}", self.palette.text.muted),
        ]
        self.update_text(build_text(lines))

    def render_data(
        self,
        payload: dict,
        status: str = "ok",
        is_lkg: bool = False,
        updated_ts_ms: int | None = None,
    ) -> None:
        funding = payload.get("funding") if isinstance(payload, dict) else None
        if not isinstance(funding, dict) or not funding:
            self.set_status_class("empty")
            lines = [
                panel_header(self.title, "empty", self.palette),
                last_updated_line(updated_ts_ms, self.palette),
                muted_line("No funding data available.", self.palette),
            ]
            self.update_text(build_text(lines))
            return
        lines: List[str] = []
        self.set_status_class("disconnected" if status == "disconnected" else "ok")
        status_value = "disconnected" if status == "disconnected" else "ok"
        styled_lines = [
            panel_header(self.title, status_value, self.palette),
            last_updated_line(updated_ts_ms, self.palette),
        ]
        if status == "disconnected" or is_lkg:
            styled_lines.append(muted_line(f"Showing last known data. Last good: {format_last_good(updated_ts_ms)}", self.palette))
        for coin, item in funding.items():
            latest = item.get("latest") if isinstance(item, dict) else None
            history = item.get("history") if isinstance(item, dict) else None
            rate = latest.get("rate") if isinstance(latest, dict) else None
            ts = latest.get("timestamp_ms") if isinstance(latest, dict) else None
            styled_lines.append((f"{coin}: rate={rate if rate is not None else 'n/a'} updated={self._fmt_ts(ts)}", self.palette.text.primary))
            if isinstance(history, list) and history:
                recent = ", ".join(
                    f"{entry.get('rate'):.5f}"
                    for entry in history[-5:]
                    if isinstance(entry, dict) and isinstance(entry.get("rate"), (int, float))
                )
                if recent:
                    styled_lines.append(muted_line(f"  recent: {recent}", self.palette))
        self.update_text(build_text(styled_lines))

    @staticmethod
    def _fmt_ts(ts_ms: int | None) -> str:
        if not ts_ms:
            return "unknown"
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
