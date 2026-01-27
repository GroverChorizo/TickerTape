"""Command bar widget with input and status line."""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import Input, Static


class CommandBar(Vertical):
    def __init__(self) -> None:
        super().__init__()
        self.input = Input(
            placeholder="Command: help | home | profile <name> | view <name>",
            id="command",
        )
        self.message = Static("", id="command_status")

    def compose(self):
        yield self.input
        yield self.message

    def set_message(self, text: str) -> None:
        self.message.update(text)

    def clear(self) -> None:
        self.input.value = ""
        self.set_message("")
