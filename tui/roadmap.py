"""Roadmap screen for missing features."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static


class RoadmapScreen(Screen):
    BINDINGS = [("escape", "close", "Close")]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Roadmap / TODO")
            yield Static(
                "- Funding feed wiring\n"
                "- Whale feed wiring\n"
                "- Live event stream sources\n"
                "- Alerts notifier auto-start",
                id="roadmap_body",
            )
