"""Bottom tab bar for compact layouts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from textual.widgets import Static


@dataclass(frozen=True)
class TabItem:
    key: str
    label: str
    short: str


class TabBar(Static):
    def __init__(self, tabs: Iterable[TabItem] | None = None, **kwargs) -> None:
        super().__init__("", **kwargs)
        self._tabs: List[TabItem] = list(tabs or [])
        self._active_index: int = 0
        self._render()

    def set_tabs(self, tabs: Iterable[TabItem]) -> None:
        self._tabs = list(tabs)
        self._active_index = min(self._active_index, max(len(self._tabs) - 1, 0))
        self._render()

    def set_active(self, key: str) -> None:
        for idx, tab in enumerate(self._tabs):
            if tab.key == key:
                self._active_index = idx
                break
        self._render()

    def select_next(self) -> None:
        if not self._tabs:
            return
        self._active_index = (self._active_index + 1) % len(self._tabs)
        self._render()

    def select_prev(self) -> None:
        if not self._tabs:
            return
        self._active_index = (self._active_index - 1) % len(self._tabs)
        self._render()

    def active_key(self) -> str:
        if not self._tabs:
            return ""
        return self._tabs[self._active_index].key

    def _render(self) -> None:
        if not self._tabs:
            self.update("")
            return
        parts: List[str] = []
        for idx, tab in enumerate(self._tabs):
            label = tab.short
            if idx == self._active_index:
                parts.append(f"[{label}]")
            else:
                parts.append(label)
        self.update(" | ".join(parts))
