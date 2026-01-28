"""Minimal Jobs screen showing recent backtest runs."""

from __future__ import annotations

from textual.widgets import Static
from textual.screen import Screen


class JobsScreen(Screen):
    def compose(self):
        yield Static("Jobs screen (use :jobs list to view runs)", id="jobs_info")
