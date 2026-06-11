"""Sidebar navigation widget and the combined SidebarContainer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from rich.text import Text
from textual.containers import Vertical
from textual.widgets import Static

from tui.state.alerts import AlertStore
from tui.themes.palettes import Palette, cypherpunk_default
from tui.widgets.alert_panel import AlertSidebarSection


@dataclass(frozen=True)
class SidebarEntry:
    key: str
    label: str
    short: str


class Sidebar(Static):
    """Profile / screen navigation list."""

    def __init__(self, entries: Iterable[SidebarEntry] | None = None, **kwargs) -> None:
        super().__init__("", **kwargs)
        self._entries: List[SidebarEntry] = list(entries or [])
        self._active_key: str = "home"
        self._compact: bool = False
        self._palette: Palette = cypherpunk_default
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

    def set_palette(self, palette: Palette) -> None:
        self._palette = palette
        try:
            self.styles.background = palette.bg.panel
            self.styles.color = palette.text.primary
        except Exception:
            pass
        self._render()

    def _render(self) -> None:
        text = Text()
        for idx, entry in enumerate(self._entries):
            if idx:
                text.append("\n")
            label = entry.short if self._compact else entry.label
            marker = ">" if entry.key == self._active_key else " "
            style = (
                f"bold {self._palette.accent.purple}"
                if entry.key == self._active_key
                else self._palette.text.muted
            )
            text.append(f"{marker} {label}", style=style)
        self.update(text)


class SidebarContainer(Vertical):
    """Left sidebar: profile navigation on top, alert history below.

    Exposes the same interface that ``BaseScreen._sync_navigation()`` uses
    on the old ``Sidebar`` widget so no profile screen needs to change.
    """

    def __init__(self, store: AlertStore | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._nav = Sidebar(id="sidebar_nav")
        self._alerts = AlertSidebarSection(store=store, id="sidebar_alerts")

    # ── Textual lifecycle ─────────────────────────────────────────────────────

    def compose(self):
        yield self._nav
        yield self._alerts

    # ── navigation delegation (mirrors Sidebar public API) ────────────────────

    def set_entries(self, entries: Iterable[SidebarEntry]) -> None:
        self._nav.set_entries(entries)

    def set_active(self, key: str) -> None:
        self._nav.set_active(key)

    def set_compact(self, compact: bool) -> None:
        self._nav.set_compact(compact)
        self._alerts.set_compact(compact)

    def set_palette(self, palette: Palette) -> None:
        self._nav.set_palette(palette)
        self._alerts.set_palette(palette)
        try:
            self.styles.background = palette.bg.panel
        except Exception:
            pass

    # ── alert store management ────────────────────────────────────────────────

    def set_alert_store(self, store: AlertStore) -> None:
        """Wire a live AlertStore into the alert section."""
        self._alerts.set_store(store)

    def refresh_alerts(self) -> None:
        """Re-render the alert section (call on every status tick)."""
        self._alerts.refresh_panel()

    def next_alert_category(self) -> str:
        """Cycle to the next alert category; return its name."""
        return self._alerts.next_category()

    def set_alert_category(self, category: str) -> None:
        self._alerts.set_category(category)
