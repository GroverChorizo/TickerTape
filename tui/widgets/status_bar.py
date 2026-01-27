"""Status bar widget for TickerTape."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from rich.text import Text
from textual.widgets import Static


class StatusBar(Static):
    def update_status(
        self,
        profile: str,
        backend_ok: bool,
        active_jobs: int,
        last_snapshot_ts: Optional[int],
        alert_count: int,
        alert_connected: bool,
        feeds: str,
    ) -> None:
        backend = "OK" if backend_ok else "MISSING"
        last_snapshot = self._fmt_ts(last_snapshot_ts)
        alert_state = "connected" if alert_connected else "disconnected"
        content = " | ".join(
            [
                f"Profile: {profile}",
                f"Backend: {backend}",
                f"Jobs: {active_jobs}",
                f"Last Snapshot: {last_snapshot}",
                f"Alerts: {alert_count} ({alert_state})",
                f"Feeds: {feeds}",
            ]
        )
        self.update(Text(content))

    @staticmethod
    def _fmt_ts(ts_ms: Optional[int]) -> str:
        if not ts_ms:
            return "unknown"
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
