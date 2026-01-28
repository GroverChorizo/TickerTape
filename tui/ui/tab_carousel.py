"""Tab carousel for open screens."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from rich.text import Text
from textual.widgets import Static

from tui.themes.palettes import Palette, cypherpunk_default


@dataclass(frozen=True)
class TabEntry:
    key: str
    label: str
    shortcut: str


class TabCarousel(Static):
    def __init__(self, tabs: Iterable[TabEntry] | None = None, **kwargs) -> None:
        super().__init__("", **kwargs)
        self._tabs: List[TabEntry] = list(tabs or [])
        self._active_index: int = 0
        self._palette: Palette = cypherpunk_default
        self._render()

    def set_tabs(self, tabs: Iterable[TabEntry]) -> None:
        self._tabs = list(tabs)
        self._active_index = min(self._active_index, max(len(self._tabs) - 1, 0))
        self._render()

    def set_active(self, key: str) -> None:
        for idx, tab in enumerate(self._tabs):
            if tab.key == key:
                self._active_index = idx
                break
        self._render()

    def select_next(self) -> str:
        if not self._tabs:
            return ""
        self._active_index = (self._active_index + 1) % len(self._tabs)
        self._render()
        return self.active_key()

    def select_prev(self) -> str:
        if not self._tabs:
            return ""
        self._active_index = (self._active_index - 1) % len(self._tabs)
        self._render()
        return self.active_key()

    def active_key(self) -> str:
        if not self._tabs:
            return ""
        return self._tabs[self._active_index].key

    def set_palette(self, palette: Palette) -> None:
        self._palette = palette
        self._render()

    def _render(self) -> None:
        if not self._tabs:
            self.update("")
            return
        text = Text()
        for idx, tab in enumerate(self._tabs):
            if idx:
                text.append(" | ", style=self._palette.text.muted)
            label = f"{tab.shortcut} {tab.label}"
            style = (
                f"bold {self._palette.accent.purple}"
                if idx == self._active_index
                else self._palette.text.muted
            )
            text.append(label, style=style)
        self.update(text)
