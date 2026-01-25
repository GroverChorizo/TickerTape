"""Positions panel for top longs/shorts."""
from __future__ import annotations

from typing import List

from .panel_base import PanelBase


class PositionsPanel(PanelBase):
    def __init__(self) -> None:
        super().__init__(panel_id="positions", title="Positions")
        self._payload: dict | None = None

    def update_payload(self, payload: dict) -> None:
        self._payload = payload

    def refresh_panel(self) -> None:
        if not self._payload:
            self.update_text("Positions feed not configured or offline.")
            return
        status = self._payload.get("status")
        data = self._payload.get("data")
        if status != "ok" or not data:
            self.update_text("Positions feed unavailable.")
            return
        lines: List[str] = ["Top Positions"]
        if isinstance(data, dict):
            for key, value in list(data.items())[:6]:
                lines.append(f"- {key}: {value}")
        else:
            lines.append("Unsupported positions payload format.")
        self.update_text("\n".join(lines))
