"""Panel base widget for TickerTape."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List

from rich.text import Text
from textual.widgets import Static


class PanelBase(Static):
    def __init__(self, panel_id: str, title: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.panel_id = panel_id
        self.border_title = title

    def set_collapsed(self, collapsed: bool) -> None:
        self.display = not collapsed

    def update_text(self, content: str | Text) -> None:
        """Update panel content using plain text (no markup)."""
        if isinstance(content, Text):
            self.update(content)
        else:
            self.update(Text(content))

    def set_status_class(self, status: str) -> None:
        for name in ("status-ok", "status-loading", "status-empty", "status-error", "status-disconnected"):
            self.remove_class(name)
        status_class = f"status-{status}"
        self.add_class(status_class)

    @staticmethod
    def format_status_line(status: str) -> str:
        labels = {
            "ok": "LIVE",
            "loading": "LOADING",
            "empty": "NO DATA",
            "error": "ERROR",
            "disconnected": "DISCONNECTED",
        }
        label = labels.get(status, status.upper())
        return f"Status: {label}"

    @staticmethod
    def format_last_good(ts_ms: int | None) -> str:
        if not ts_ms:
            return "none"
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

    def format_error_footer(self, error: str, updated_ts_ms: int | None, backoff_note: str) -> List[str]:
        return [
            "Feed Error",
            self.format_status_line("error"),
            f"Error: {error}",
            f"Backoff: {backoff_note}",
            f"Last good: {self.format_last_good(updated_ts_ms)}",
        ]

    def join_lines(self, lines: Iterable[str]) -> str:
        return "\n".join(line for line in lines if line)
