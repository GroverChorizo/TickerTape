"""Base screen for TickerTape profiles."""
from __future__ import annotations

from textual.screen import Screen
from textual.widgets import Static, Input
from textual.containers import Vertical

from tui.ui.widgets.command_bar import CommandBar


class BaseScreen(Screen):
    BINDINGS = [("ctrl+p", "focus_command", "Focus command")]

    def __init__(self, *, screen_id: str, title: str, context: str) -> None:
        super().__init__(id=screen_id)
        self.screen_title = title
        self.command_context = context
        self.header = Static("", id="screen_header")
        self.status = Static("", id="status_strip")
        self.body = Static("", id="screen_body")
        self.command_bar = CommandBar()

    def compose(self):
        with Vertical(id="screen_root"):
            yield self.header
            yield self.status
            yield self.body
            yield self.command_bar

    def set_header(self, text: str) -> None:
        self.header.update(text)

    def set_status(self, text: str) -> None:
        self.status.update(text)

    def action_focus_command(self) -> None:
        try:
            self.command_bar.input.focus()
        except Exception:
            pass

    def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value.strip()
        self.command_bar.clear()
        if not command:
            return
        handler = getattr(self.app, "dispatch_command", None)
        if handler:
            handler(command, context=self.command_context)
