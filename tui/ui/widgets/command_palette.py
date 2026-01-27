"""Command palette widget."""

from __future__ import annotations

from typing import Iterable, List

from textual.containers import Vertical
from textual.widgets import Input, Static


class CommandPalette(Vertical):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.input = Input(placeholder="Type a command or route...", id="palette_input")
        self.suggestions = Static("", id="palette_suggestions")
        self._items: List[str] = []
        self._index: int = 0

    def compose(self):
        yield self.input
        yield self.suggestions

    def set_items(self, items: Iterable[str]) -> None:
        self._items = list(items)
        self._index = 0 if self._items else -1
        self._render()

    def select_next(self) -> None:
        if not self._items:
            return
        self._index = (self._index + 1) % len(self._items)
        self._render()

    def select_prev(self) -> None:
        if not self._items:
            return
        self._index = (self._index - 1) % len(self._items)
        self._render()

    def current_item(self) -> str:
        if self._items and 0 <= self._index < len(self._items):
            return self._items[self._index]
        return ""

    def _render(self) -> None:
        if not self._items:
            self.suggestions.update("No matches.")
            return
        lines: List[str] = []
        for idx, item in enumerate(self._items):
            marker = ">" if idx == self._index else " "
            lines.append(f"{marker} {item}")
        self.suggestions.update("\n".join(lines))
