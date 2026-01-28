"""Liquidations radar panel for Liquidation Hunter."""

from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import List, Optional

from tui.render.palette import (
    build_text,
    heading_line,
    last_updated_line,
    muted_line,
    panel_header,
)
from tui.render.sparkline import sparkline
from tui.feeds.base import FeedResult, FeedStatus, _as_status
from .panel_base import PanelBase


class LiquidationsRadarPanel(PanelBase):
    def __init__(self) -> None:
        super().__init__(panel_id="liquidations_radar", title="Liquidations Radar")
        self.feed_result = FeedResult(status="loading")
        self._selected_symbol: Optional[str] = None

    def update_feed(
        self, result: FeedResult, *, selected_symbol: Optional[str] = None
    ) -> None:
        self.feed_result = result
        if selected_symbol:
            self._selected_symbol = selected_symbol
        self.refresh_panel()

    def refresh_panel(self) -> None:
        status = _as_status(self.feed_result.status)
        if status == FeedStatus.LOADING:
            self._render_loading()
            return
        if status in {FeedStatus.ERROR, FeedStatus.DISCONNECTED} and not self.feed_result.data:
            self._render_error(
                self.feed_result.error or "Unknown error",
                hint="Check API key or endpoint availability.",
                updated_ts_ms=self.feed_result.updated_ts_ms,
            )
            return
        if status == FeedStatus.EMPTY and not self.feed_result.data:
            self._render_empty("No data yet.")
            return
        self._render_data(self.feed_result)

    def _render_loading(self) -> None:
        self.set_status_class("loading")
        lines = [
            panel_header(self.title, "loading", self.palette),
            last_updated_line(self.feed_result.updated_ts_ms, self.palette),
            muted_line("Loading liquidation radar...", self.palette),
        ]
        self.update_text(build_text(lines))

    def _render_empty(self, reason: str) -> None:
        self.set_status_class("empty")
        lines = [
            panel_header(self.title, "empty", self.palette),
            last_updated_line(self.feed_result.updated_ts_ms, self.palette),
            muted_line(f"No data. {reason}", self.palette),
        ]
        self.update_text(build_text(lines))

    def _render_error(
        self, error: str, hint: str, updated_ts_ms: Optional[int]
    ) -> None:
        self.set_status_class("error")
        lines = [
            panel_header(self.title, "error", self.palette),
            last_updated_line(updated_ts_ms, self.palette),
            (error, self.palette.text.primary),
            (f"Hint: {hint}", self.palette.text.muted),
        ]
        self.update_text(build_text(lines))

    def _render_data(self, result: FeedResult) -> None:
        payload = result.data or {}
        rollups = payload.get("rollups", {}) if isinstance(payload, dict) else {}
        series = payload.get("series", {}) if isinstance(payload, dict) else {}
        cascade = payload.get("cascade", {}) if isinstance(payload, dict) else {}
        events = payload.get("events", []) if isinstance(payload, dict) else []
        errors = payload.get("errors", []) if isinstance(payload, dict) else []

        status = _as_status(result.status)
        self.set_status_class(
            FeedStatus.DISCONNECTED.value if status == FeedStatus.DISCONNECTED else FeedStatus.OK.value
        )
        status_value = FeedStatus.DISCONNECTED.value if status == FeedStatus.DISCONNECTED else FeedStatus.OK.value
        lines: List[tuple[str, str]] = []
        lines.append(panel_header(self.title, status_value, self.palette))
        lines.append(last_updated_line(result.updated_ts_ms, self.palette))
        if status == FeedStatus.DISCONNECTED or result.is_lkg:
            stale = _fmt_stale(result.updated_ts_ms)
            lines.append(
                muted_line(f"Showing last known data. Stale {stale}", self.palette)
            )
        if isinstance(errors, list) and errors:
            lines.append(
                muted_line("Partial errors: " + "; ".join(errors[:2]), self.palette)
            )

        lines.append(heading_line("Rolling totals", self.palette))
        for label in ("1m", "5m", "15m"):
            window = rollups.get(label, {}) if isinstance(rollups, dict) else {}
            lines.append(self._format_rollup(label, window))

        spark = (
            sparkline(series.get("notional", []), width=16)
            if isinstance(series, dict)
            else ""
        )
        if spark:
            lines.append((f"Notional trend: {spark}", self.palette.text.primary))

        if isinstance(cascade, dict):
            level = cascade.get("level", "LOW")
            reason = cascade.get("reason", "")
            if level == "HIGH":
                style = self.palette.accent.red
            elif level == "MED":
                style = self.palette.accent.orange
            else:
                style = self.palette.accent.green
            lines.append(
                (
                    f"Cascade risk: {level} ({reason})",
                    f"bold {style}",
                )
            )

        lines.append(heading_line("Recent liquidations", self.palette))
        if self._selected_symbol:
            lines.append(muted_line(f"Focus: {self._selected_symbol}", self.palette))
        if not isinstance(events, list) or not events:
            lines.append(muted_line("No recent liquidation events.", self.palette))
        else:
            recent = events
            if self._selected_symbol:
                recent = [
                    e
                    for e in events
                    if str(e.get("symbol") or "").upper() == self._selected_symbol
                ]
            for event in recent[:6]:
                lines.append(self._format_event(event))

        self.update_text(build_text(lines))

    def _format_rollup(self, label: str, window: dict) -> tuple[str, str]:
        count = window.get("count") or 0
        notional = _fmt_usd(window.get("notional"))
        long_count = window.get("long_count") or 0
        short_count = window.get("short_count") or 0
        ratio = _ratio(long_count, short_count)
        return (
            f"{label}: {count} liqs | {notional} | L/S {long_count}/{short_count} ({ratio})",
            self.palette.text.primary,
        )

    def _format_event(self, event: dict) -> tuple[str, str]:
        ts = _fmt_ts(event.get("ts_ms"))
        symbol = event.get("symbol", "?")
        side = event.get("side", "?")
        notional = _fmt_usd(event.get("notional_usd"))
        style = (
            self.palette.accent.green if side == "long_liq" else self.palette.accent.red
        )
        return (f"[{ts}] {symbol} {side} {notional}", style)


def _fmt_ts(ts_ms: Optional[int]) -> str:
    if not ts_ms:
        return "--"
    dt = datetime.fromtimestamp(int(ts_ms) / 1000, tz=timezone.utc)
    return dt.strftime("%H:%M:%S")


def _fmt_usd(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    try:
        value_f = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if value_f >= 1_000_000:
        return f"${value_f / 1_000_000:.2f}M"
    if value_f >= 1_000:
        return f"${value_f / 1_000:.1f}K"
    return f"${value_f:,.0f}"


def _ratio(long_count: int, short_count: int) -> str:
    total = long_count + short_count
    if total <= 0:
        return "n/a"
    pct_long = (long_count / total) * 100
    if pct_long >= 60:
        return f"{pct_long:.0f}% L"
    if pct_long <= 40:
        return f"{100 - pct_long:.0f}% S"
    return "balanced"


def _fmt_stale(updated_ts_ms: Optional[int]) -> str:
    if not updated_ts_ms:
        return "unknown"
    delta = int(time.time() * 1000) - int(updated_ts_ms)
    if delta < 0:
        delta = 0
    return f"+{int(delta / 1000)}s"
