"""Modal command palette screen."""

from __future__ import annotations

from textual import events
from textual.screen import ModalScreen
from textual.containers import Vertical

from tui.ui.widgets.command_palette import CommandPalette


class CommandPaletteScreen(ModalScreen):
    BINDINGS = [
        ("escape", "close", "Close"),
        ("up", "prev", "Previous"),
        ("down", "next", "Next"),
    ]

    def __init__(self, *, context: str) -> None:
        super().__init__()
        self._context = context
        self.palette = CommandPalette(id="command_palette")

    def compose(self):
        with Vertical(id="palette_root"):
            yield self.palette

    def on_mount(self) -> None:
        self._refresh_suggestions("")
        self.palette.input.focus()

    def action_close(self) -> None:
        self.dismiss(False)

    def action_prev(self) -> None:
        self.palette.select_prev()

    def action_next(self) -> None:
        self.palette.select_next()

    def on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            self._submit_selection()
            event.stop()

    def on_input_changed(self, event) -> None:
        if event.input.id != "palette_input":
            return
        self._refresh_suggestions(event.value)

    def on_input_submitted(self, event) -> None:
        if event.input.id != "palette_input":
            return
        self._submit_selection()

    def _refresh_suggestions(self, query: str) -> None:
        getter = getattr(self.app, "palette_suggestions", None)
        if getter:
            items = getter(query)
        else:
            items = []
        self.palette.set_items(items)

    def _submit_selection(self) -> None:
        raw = self.palette.current_item() or self.palette.input.value
        command = raw.split(" - ")[0].strip()
        if command:
            handler = getattr(self.app, "dispatch_command", None)
            if handler:
                handler(command, context=self._context)
        self.dismiss(True)
