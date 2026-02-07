"""Panel base widget for TickerTape."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from tui.themes.palettes import Palette, cypherpunk_default


class PanelBase(Static):
    def __init__(self, panel_id: str, title: str, **kwargs) -> None:
        if "id" not in kwargs:
            kwargs["id"] = panel_id
        super().__init__(**kwargs)
        self.panel_id = panel_id
        self.title = title
        self.border_title = title
        self.add_class("panel")
        self.palette: Palette = cypherpunk_default
        self._status: str = "ok"
        self._focused: bool = False
        self._alert: bool = False

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

    def set_alert(self, alert: bool) -> None:
        self._alert = alert
        self._apply_border()

    def clear_alert(self) -> None:
        self.set_alert(False)

    def trigger_alert(self, duration: float = 1.5) -> None:
        self.set_alert(True)
        try:
            self.set_timer(duration, self.clear_alert)
        except Exception:
            pass

    def _apply_border(self) -> None:
        if not self.palette:
            return
        if self._alert:
            self.styles.border = ("heavy", self.palette.accent.red)
        elif self._status == "error":
            self.styles.border = ("heavy", self.palette.accent.orange)
        elif self._status == "disconnected":
            self.styles.border = ("tall", self.palette.accent.orange)
        elif self._focused:
            self.styles.border = ("heavy", self.palette.border.focus)
        else:
            self.styles.border = ("tall", self.palette.border.panel)


class ResizablePanel(PanelBase):
    def __init__(
        self,
        panel_id: str,
        title: str,
        *,
        min_width: int = 20,
        min_height: int = 5,
        **kwargs,
    ) -> None:
        super().__init__(panel_id=panel_id, title=title, **kwargs)
        self._min_width = min_width
        self._min_height = min_height
        self._resizing = False
        self._resize_origin: tuple[int, int] | None = None
        self._size_origin: tuple[int, int] | None = None

    def on_mouse_down(self, event) -> None:
        self._resizing = True
        self._resize_origin = (event.screen_x, event.screen_y)
        self._size_origin = (self.size.width, self.size.height)

    def on_mouse_up(self, _event) -> None:
        self._resizing = False
        self._resize_origin = None
        self._size_origin = None

    def on_mouse_move(self, event) -> None:
        if not self._resizing or not self._resize_origin or not self._size_origin:
            return
        delta_x = event.screen_x - self._resize_origin[0]
        delta_y = event.screen_y - self._resize_origin[1]
        width = self._size_origin[0] + delta_x
        height = self._size_origin[1] + delta_y
        self.resize_to(width, height)

    def resize_by(self, delta_w: int, delta_h: int) -> tuple[int, int]:
        width = _scalar_to_int(self.styles.width, self.size.width) + delta_w
        height = _scalar_to_int(self.styles.height, self.size.height) + delta_h
        return self.resize_to(width, height)

    def resize_to(self, width: int, height: int) -> tuple[int, int]:
        width = max(self._min_width, width)
        height = max(self._min_height, height)
        self.styles.width = width
        self.styles.height = height
        return width, height


def _scalar_to_int(value, fallback: int) -> int:
    if value is None:
        return int(fallback)
    if isinstance(value, (int, float)):
        return int(value)
    scalar_value = getattr(value, "value", None)
    if isinstance(scalar_value, (int, float)):
        return int(scalar_value)
    return int(fallback)
