"""Funding rates panel with explicit missing-data messaging."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from rich.text import Text

from ..feeds.base import FeedResult
from tui.render.palette import (
    build_text,
    format_last_good,
    heading_line,
    last_updated_line,
    muted_line,
    panel_header,
    status_style,
)
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
        rows = payload.get("rows") if isinstance(payload, dict) else None
        if not isinstance(rows, list) or not rows:
            self.set_status_class("empty")
            lines = [
                panel_header(self.title, "empty", self.palette),
                last_updated_line(updated_ts_ms, self.palette),
                muted_line("No funding data available.", self.palette),
            ]
            self.update_text(build_text(lines))
            return
        lines: List[tuple[str, str] | Any] = []
        self.set_status_class("disconnected" if status == "disconnected" else "ok")
        status_value = "disconnected" if status == "disconnected" else "ok"
        styled_lines = [
            panel_header(self.title, status_value, self.palette),
            last_updated_line(updated_ts_ms, self.palette),
        ]
        if status == "disconnected" or is_lkg:
            styled_lines.append(
                muted_line(
                    f"Showing last known data. Last good: {format_last_good(updated_ts_ms)}",
                    self.palette,
                )
            )
        errors = payload.get("errors") if isinstance(payload, dict) else None
        if isinstance(errors, list) and errors:
            styled_lines.append(
                muted_line("Partial errors: " + "; ".join(errors[:3]), self.palette)
            )
        styled_lines.extend(self._render_table(rows))
        self.update_text(build_text(styled_lines))

    @staticmethod
    def _fmt_ts(ts_ms: int | None) -> str:
        if not ts_ms:
            return "unknown"
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

    def _render_table(self, rows: List[Dict[str, Any]]) -> List[Any]:
        sorted_rows = sorted(
            rows,
            key=lambda row: abs(row.get("annualized_pct") or 0.0),
            reverse=True,
        )
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for row in sorted_rows:
            symbol = str(row.get("symbol") or "?")
            grouped.setdefault(symbol, []).append(row)

        lines: List[Any] = []
        lines.append(
            heading_line(
                "Exchange | Symbol | Rate | Annualized | Spread | Updated | Arb | Status",
                self.palette,
            )
        )
        for symbol, group in grouped.items():
            lines.append(muted_line(f"{symbol}", self.palette))
            for row in group:
                lines.append(self._format_row(row))
        return lines

    def _format_row(self, row: Dict[str, Any]):
        exchange = str(row.get("exchange") or "?")
        symbol = str(row.get("symbol") or "?")
        rate = row.get("rate")
        annualized = row.get("annualized_pct")
        interval = row.get("interval_hours")
        timestamp = row.get("timestamp_ms")
        status = str(row.get("status") or "STALE").upper()
        rate_str = self._fmt_rate(rate, interval)
        ann_str = self._fmt_percent(annualized)
        spread_str = self._fmt_percent(row.get("spread_pct"))
        ts_str = self._fmt_short_ts(timestamp)
        arb = bool(row.get("arbitrage"))
        arb_label = "ARB" if arb else "-"
        row_text = Text()
        row_text.append(
            f"{exchange:<12} | {symbol:<6} | {rate_str:<10} | {ann_str:<10} | {spread_str:<8} | {ts_str:<8} | ",
            style=self.palette.text.primary,
        )
        row_text.append(
            f"{arb_label:<3} | ",
            style=f"bold {status_style('ok' if arb else 'empty', self.palette)}",
        )
        row_text.append(
            status,
            style=f"bold {status_style(status.lower(), self.palette)}",
        )
        return row_text

    @staticmethod
    def _fmt_rate(rate: Any, interval_hours: Any) -> str:
        try:
            value = float(rate)
        except (TypeError, ValueError):
            return "n/a"
        suffix = (
            f"/{interval_hours}h" if isinstance(interval_hours, (int, float)) else ""
        )
        return f"{value:+.6f}{suffix}"

    @staticmethod
    def _fmt_percent(value: Any) -> str:
        try:
            return f"{float(value):+.2f}%"
        except (TypeError, ValueError):
            return "n/a"

    @staticmethod
    def _fmt_short_ts(ts_ms: Any) -> str:
        if not ts_ms:
            return "unknown"
        try:
            ts_int = int(ts_ms)
        except (TypeError, ValueError):
            return "unknown"
        dt = datetime.fromtimestamp(ts_int / 1000, tz=timezone.utc)
        return dt.strftime("%H:%M:%S")
