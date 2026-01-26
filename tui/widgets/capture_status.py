"""Capture/export status panel for liquidation data."""
from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import Optional

from tui.render.palette import build_text, last_updated_line, muted_line, panel_header
from tui.feeds.base import FeedResult
from .panel_base import PanelBase


class CaptureStatusPanel(PanelBase):
    def __init__(self) -> None:
        super().__init__(panel_id="capture_status", title="Capture Status")
        self.feed_result = FeedResult(status="loading")

    def update_feed(self, result: FeedResult) -> None:
        self.feed_result = result
        self.refresh_panel()

    def refresh_panel(self) -> None:
        status = self.feed_result.status
        if status == "loading":
            self._render_loading()
            return
        if status in {"error", "disconnected"} and not self.feed_result.data:
            self._render_error(self.feed_result.error or "Unknown error")
            return
        self._render_data()

    def _render_loading(self) -> None:
        self.set_status_class("loading")
        lines = [
            panel_header(self.title, "loading", self.palette),
            last_updated_line(self.feed_result.updated_ts_ms, self.palette),
            muted_line("Loading capture status...", self.palette),
        ]
        self.update_text(build_text(lines))

    def _render_error(self, error: str) -> None:
        self.set_status_class("error")
        lines = [
            panel_header(self.title, "error", self.palette),
            last_updated_line(self.feed_result.updated_ts_ms, self.palette),
            (error, self.palette.text.primary),
            ("Hint: Check capture command and storage path.", self.palette.text.muted),
        ]
        self.update_text(build_text(lines))

    def _render_data(self) -> None:
        payload = self.feed_result.data or {}
        capture = payload.get("capture") if isinstance(payload, dict) else None
        enabled = capture.get("enabled") if isinstance(capture, dict) else False
        status_value = "ok" if enabled else "empty"
        self.set_status_class("disconnected" if self.feed_result.status == "disconnected" else status_value)
        header_status = "ok" if enabled else "empty"
        lines = [
            panel_header(self.title, header_status, self.palette),
            last_updated_line(self.feed_result.updated_ts_ms, self.palette),
        ]
        if self.feed_result.status == "disconnected" or self.feed_result.is_lkg:
            lines.append(muted_line(f"Showing last known data. Stale {_fmt_stale(self.feed_result.updated_ts_ms)}", self.palette))
        if not isinstance(capture, dict):
            lines.append(muted_line("Capture data unavailable.", self.palette))
            self.update_text(build_text(lines))
            return
        on_off = "ON" if enabled else "OFF"
        lines.append((f"Capture: {on_off}", self.palette.text.primary))
        lines.append((f"Output: {capture.get('base_path', '-')}", self.palette.text.primary))
        lines.append((f"Files: {capture.get('file_count', 0)} | Size: {_fmt_bytes(capture.get('total_bytes'))}", self.palette.text.primary))
        lines.append((f"Last export: {_fmt_ts(capture.get('last_export_ts_ms'))}", self.palette.text.primary))
        lines.append(muted_line("Backtests use local data only.", self.palette))
        self.update_text(build_text(lines))


def _fmt_ts(ts_ms: Optional[int]) -> str:
    if not ts_ms:
        return "never"
    dt = datetime.fromtimestamp(int(ts_ms) / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def _fmt_bytes(value: Optional[int]) -> str:
    if not value:
        return "0 B"
    size = float(value)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _fmt_stale(updated_ts_ms: Optional[int]) -> str:
    if not updated_ts_ms:
        return "unknown"
    delta = int(time.time() * 1000) - int(updated_ts_ms)
    if delta < 0:
        delta = 0
    return f"+{int(delta / 1000)}s"
