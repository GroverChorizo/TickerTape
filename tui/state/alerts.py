"""Alert stream state for the TUI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List
import json
import asyncio

from tickertape.core.alerts import AlertEvent, AlertSeverity


@dataclass(frozen=True)
class AlertMessage:
    alert_type: str
    severity: AlertSeverity
    source_feed: str
    timestamp_ms: int
    payload: Dict

    @classmethod
    def from_json(cls, line: str) -> "AlertMessage":
        data = json.loads(line)
        severity_raw = data.get("severity", "info")
        try:
            severity = AlertSeverity(severity_raw)
        except Exception:
            severity = AlertSeverity.INFO
        return cls(
            alert_type=data.get("alert_type", "unknown"),
            severity=severity,
            source_feed=data.get("source_feed", "unknown"),
            timestamp_ms=int(data.get("timestamp_ms", 0)),
            payload=data.get("payload", {}),
        )

    def to_event(self) -> AlertEvent:
        return AlertEvent(
            alert_type=self.alert_type,
            severity=self.severity,
            source_feed=self.source_feed,
            timestamp_ms=self.timestamp_ms,
            payload=self.payload,
        )


class AlertStore:
    def __init__(self, max_size: int = 200) -> None:
        self.max_size = max_size
        self.alerts: List[AlertEvent] = []
        self.muted = False

    def add(self, alert: AlertEvent) -> None:
        self.alerts.append(alert)
        if len(self.alerts) > self.max_size:
            self.alerts = self.alerts[-self.max_size :]

    def clear(self) -> None:
        self.alerts = []

    def set_muted(self, muted: bool) -> None:
        self.muted = bool(muted)


class AlertStream:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        *,
        store: AlertStore | None = None,
        on_alert: Callable[[AlertEvent], None] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.alerts: List[AlertMessage] = []
        self.store = store
        self.on_alert = on_alert
        self.connected = False
        self._task: asyncio.Task | None = None

    async def connect(self) -> None:
        try:
            reader, _writer = await asyncio.open_connection(self.host, self.port)
            self.connected = True
            while True:
                line = await reader.readline()
                if not line:
                    break
                try:
                    alert = AlertMessage.from_json(line.decode("utf-8"))
                    self.alerts.append(alert)
                    self.alerts = self.alerts[-200:]
                    if self.store:
                        self.store.add(alert.to_event())
                    if self.on_alert:
                        try:
                            self.on_alert(alert.to_event())
                        except Exception:
                            pass
                except Exception:
                    continue
        except Exception:
            self.connected = False
        finally:
            self.connected = False

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.connect())
