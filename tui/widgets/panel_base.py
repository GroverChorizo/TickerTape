"""Panel base widget for TickerTape."""
from __future__ import annotations

from textual.widgets import Static


class PanelBase(Static):
    def __init__(self, panel_id: str, title: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.panel_id = panel_id
        self.border_title = title

    def set_collapsed(self, collapsed: bool) -> None:
        self.display = not collapsed
