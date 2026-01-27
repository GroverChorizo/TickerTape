"""Panel base widget for TickerTape."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from tui.themes.palettes import Palette, cypherpunk_default


class PanelBase(Static):
    def __init__(self, panel_id: str, title: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.panel_id = panel_id
        self.title = title
        self.border_title = title
        self.palette: Palette = cypherpunk_default
        self._status: str = "ok"
        self._focused: bool = False

    def set_collapsed(self, collapsed: bool) -> None:
        self.display = not collapsed

    @property
    def content(self):
        """Compat for tests/helpers: return the current renderable (what Static is showing)."""
        # Textual Static keeps the current display value in `renderable`
        return getattr(self, "renderable", None)

    def update_text(self, content: str | Text) -> None:
        """Update panel content using plain text (no markup)."""
        if isinstance(content, Text):
            self.update(content)
        else:
            self.update(Text(content))

    def set_palette(self, palette: Palette) -> None:
        self.palette = palette
        self.styles.background = palette.bg.panel
        self.styles.border = ("tall", palette.border.panel)
        self.styles.color = palette.text.primary
        self._apply_border()

    def set_status_class(self, status: str) -> None:
        self._status = status
        self._apply_border()

    def set_focus(self, focused: bool) -> None:
        self._focused = focused
        self._apply_border()

    def _apply_border(self) -> None:
        if not self.palette:
            return
        if self._status == "error":
            self.styles.border = ("heavy", self.palette.accent.orange)
        elif self._status == "disconnected":
            self.styles.border = ("tall", self.palette.accent.orange)
        elif self._focused:
            self.styles.border = ("heavy", self.palette.border.focus)
        else:
            self.styles.border = ("tall", self.palette.border.panel)
