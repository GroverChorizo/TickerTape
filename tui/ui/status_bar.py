"""Status bar with breadcrumb line."""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import Static


class StatusBar(Vertical):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.status_line = Static("", id="status_line")
        self.breadcrumb_line = Static("", id="breadcrumb_line")

    def compose(self):
        yield self.status_line
        yield self.breadcrumb_line

    def set_status(self, text: str) -> None:
        self.status_line.update(text)

    def set_breadcrumb(self, text: str) -> None:
        self.breadcrumb_line.update(text)
