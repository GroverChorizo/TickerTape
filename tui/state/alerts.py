"""Alert stream state for the TUI."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
import json
import asyncio


@dataclass
class AlertMessage:
    alert_type: str
    severity: str
    source_feed: str
    timestamp_ms: int
    payload: Dict

    @classmethod
    def from_json(cls, line: str) -> "AlertMessage":
        data = json.loads(line)
        return cls(
            alert_type=data.get("alert_type", "unknown"),
            severity=data.get("severity", "unknown"),
            source_feed=data.get("source_feed", "unknown"),
            timestamp_ms=int(data.get("timestamp_ms", 0)),
            payload=data.get("payload", {}),
        )


class AlertStream:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self.alerts: List[AlertMessage] = []
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
                except Exception:
                    continue
        except Exception:
            self.connected = False
        finally:
            self.connected = False

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.connect())
