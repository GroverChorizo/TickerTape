"""Alerts panel showing backend alerts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ..state.alerts import AlertStream
from .panel_base import PanelBase


class AlertPanel(PanelBase):
    def __init__(self, stream: AlertStream) -> None:
        super().__init__(panel_id="alerts", title="Alerts")
        self.stream = stream

    def refresh_panel(self) -> None:
        if not self.stream.connected:
            if not self.stream.alerts:
                self.update_text(
                    "Alert stream disconnected. Start backend alert notifier to receive alerts."
                )
                return
        if not self.stream.alerts:
            self.update_text("No alerts received.")
            return
        lines: List[str] = []
        for alert in self.stream.alerts[-8:]:
            ts = datetime.fromtimestamp(alert.timestamp_ms / 1000, tz=timezone.utc)
            lines.append(
                f"[{ts.strftime('%H:%M:%S')}] {alert.severity.upper()} {alert.alert_type} ({alert.source_feed})"
            )
        self.update_text("\n".join(lines))
