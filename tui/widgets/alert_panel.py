"""Alerts panel showing backend alerts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ..state.alerts import AlertStore
from .panel_base import PanelBase


class AlertPanel(PanelBase):
    def __init__(self, store: AlertStore) -> None:
        super().__init__(panel_id="alerts", title="Alerts")
        self.store = store

    def refresh_panel(self) -> None:
        if not self.store.alerts:
            self.update_text("No alerts received.")
            return
        lines: List[str] = []
        for alert in self.store.alerts[-8:]:
            ts = datetime.fromtimestamp(alert.timestamp_ms / 1000, tz=timezone.utc)
            lines.append(
                f"[{ts.strftime('%H:%M:%S')}] {alert.severity.value.upper()} {alert.alert_type} ({alert.source_feed})"
            )
        self.update_text("\n".join(lines))
