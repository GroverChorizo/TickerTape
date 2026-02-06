"""Liquidations panel: live liquidation stats."""

from __future__ import annotations

from datetime import datetime, timezone

from ..feeds.base import FeedResult, FeedStatus, _as_status
from tui.render.palette import (
    build_text,
    format_last_good,
    last_updated_line,
    muted_line,
    panel_header,
)
from .panel_base import PanelBase


class LiquidationsPanel(PanelBase):
    def __init__(self) -> None:
        super().__init__(panel_id="liquidations", title="Liquidations")
        self.feed_result = FeedResult(status="loading")

    def update_feed(self, result: FeedResult) -> None:
        self.feed_result = result
        self.refresh_panel()

    def refresh_panel(self) -> None:
        status = _as_status(self.feed_result.status)
        if status == FeedStatus.LOADING:
            self.render_loading()
            return
        if status in {FeedStatus.ERROR, FeedStatus.DISCONNECTED} and not self.feed_result.data:
            self.render_error(
                self.feed_result.error or "Unknown error",
                hint="Check API base URL or endpoint availability.",
                updated_ts_ms=self.feed_result.updated_ts_ms,
            )
            return
        if status == FeedStatus.EMPTY and not self.feed_result.data:
            self.render_empty("No data yet.")
            return
        self.render_data(
            self.feed_result.data,
            status=status,
            is_lkg=self.feed_result.is_lkg,
            updated_ts_ms=self.feed_result.updated_ts_ms,
        )

    def render_loading(self) -> None:
        self.set_status_class(FeedStatus.LOADING.value)
        lines = [
            panel_header(self.title, FeedStatus.LOADING.value, self.palette),
            last_updated_line(self.feed_result.updated_ts_ms, self.palette),
            muted_line("Loading liquidation stats...", self.palette),
        ]
        self.update_text(build_text(lines))

    def render_empty(self, reason: str) -> None:
        self.set_status_class(FeedStatus.EMPTY.value)
        lines = [
            panel_header(self.title, FeedStatus.EMPTY.value, self.palette),
            last_updated_line(self.feed_result.updated_ts_ms, self.palette),
            muted_line(f"No data. {reason}", self.palette),
        ]
        self.update_text(build_text(lines))

    def render_error(self, error: str, hint: str, updated_ts_ms: int | None) -> None:
        self.set_status_class(FeedStatus.ERROR.value)
        lines = [
            panel_header(self.title, FeedStatus.ERROR.value, self.palette),
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
        snapshot = payload.get("snapshot") if isinstance(payload, dict) else None
        if not isinstance(snapshot, dict):
            self.set_status_class("empty")
            lines = [
                panel_header(self.title, "empty", self.palette),
                last_updated_line(updated_ts_ms, self.palette),
                muted_line("No liquidation snapshot data available.", self.palette),
            ]
            self.update_text(build_text(lines))
            return
        self.set_status_class(FeedStatus.DISCONNECTED.value if status == FeedStatus.DISCONNECTED else FeedStatus.OK.value)
        status_value = FeedStatus.DISCONNECTED.value if status == FeedStatus.DISCONNECTED else FeedStatus.OK.value
        styled_lines = [
            panel_header(self.title, status_value, self.palette),
            last_updated_line(updated_ts_ms, self.palette),
        ]
        if status == FeedStatus.DISCONNECTED or is_lkg:
            styled_lines.append(
                muted_line(
                    f"Showing last known data. Last good: {format_last_good(updated_ts_ms)}",
                    self.palette,
                )
            )
        total = snapshot.get("total_notional")
        count = snapshot.get("count")
        cascade = snapshot.get("cascade_detected")
        velocity = snapshot.get("velocity_score")
        computed = snapshot.get("computed_at_ts_ms") or snapshot.get("timestamp_ms")
        styled_lines.append(
            (f"Total notional: {self._fmt_money(total)}", self.palette.text.primary)
        )
        styled_lines.append(
            (
                f"Count: {count if count is not None else 'n/a'}",
                self.palette.text.primary,
            )
        )
        styled_lines.append(
            (f"Cascade: {'YES' if cascade else 'no'}", self.palette.text.primary)
        )
        if velocity is not None:
            styled_lines.append((f"Velocity: {velocity}", self.palette.text.primary))
        styled_lines.append(
            (f"Updated: {self._fmt_ts(computed)}", self.palette.text.muted)
        )
        top_symbols = snapshot.get("top_symbols", [])
        if isinstance(top_symbols, list) and top_symbols:
            top_fmt = ", ".join(
                f"{item.get('symbol', '?')} {self._fmt_money(item.get('notional'))}"
                for item in top_symbols[:3]
            )
            styled_lines.append((f"Top symbols: {top_fmt}", self.palette.text.primary))
        self.update_text(build_text(styled_lines))

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
