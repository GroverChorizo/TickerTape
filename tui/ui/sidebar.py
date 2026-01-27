"""Sidebar navigation widget."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from textual.widgets import Static


@dataclass(frozen=True)
class SidebarEntry:
    key: str
    label: str
    short: str


class Sidebar(Static):
    def __init__(self, entries: Iterable[SidebarEntry] | None = None, **kwargs) -> None:
        super().__init__("", **kwargs)
        self._entries: List[SidebarEntry] = list(entries or [])
        self._active_key: str = "home"
        self._compact: bool = False
        self._render()

    def set_entries(self, entries: Iterable[SidebarEntry]) -> None:
        self._entries = list(entries)
        self._render()

    def set_active(self, key: str) -> None:
        self._active_key = key
        self._render()

    def set_compact(self, compact: bool) -> None:
        self._compact = compact
        self._render()

    def _render(self) -> None:
        lines: List[str] = []
        for entry in self._entries:
            label = entry.short if self._compact else entry.label
            marker = ">" if entry.key == self._active_key else " "
            lines.append(f"{marker} {label}")
        self.update("\n".join(lines))
