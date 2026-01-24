"""AlertManager and simple TCP notifier for frontend consumption.

- Alert messages are JSON lines sent to connected TCP clients (host/port configurable)
- Alert schema: alert_type, severity, source_feed, timestamp_ms, payload
"""
from __future__ import annotations
import asyncio
import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Callable
import logging
import time

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    alert_type: str
    severity: str
    source_feed: str
    timestamp_ms: int
    payload: Dict[str, Any]

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))


class SocketNotifier:
    """Simple TCP server that broadcasts JSON alert messages to connected clients.

    Designed for local development and testing (frontend can connect via localhost).
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self._server: Optional[asyncio.AbstractServer] = None
        self._clients: List[asyncio.StreamWriter] = []

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        addr = writer.get_extra_info("peername")
        logger.info({"event": "client_connected", "addr": addr})
        self._clients.append(writer)
        try:
            while not reader.at_eof():
                # keep connection open; read but ignore input
                data = await reader.read(100)
                if not data:
                    break
        finally:
            logger.info({"event": "client_disconnected", "addr": addr})
            try:
                self._clients.remove(writer)
            except ValueError:
                pass
            writer.close()
            await writer.wait_closed()

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, self.host, self.port)
        logger.info({"event": "socket_notifier_started", "host": self.host, "port": self.port})

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        # close clients
        for w in list(self._clients):
            try:
                w.close()
                await w.wait_closed()
            except Exception:
                pass
        self._clients = []

    async def notify(self, alert: Alert) -> None:
        msg = alert.to_json() + "\n"
        to_remove: List[asyncio.StreamWriter] = []
        for w in list(self._clients):
            try:
                w.write(msg.encode("utf-8"))
                await w.drain()
            except Exception as e:
                logger.warning({"event": "notify_failed", "err": str(e)})
                to_remove.append(w)
        for w in to_remove:
            try:
                self._clients.remove(w)
            except ValueError:
                pass


class AlertManager:
    def __init__(self, notifier: SocketNotifier) -> None:
        self.notifier = notifier
        self.alert_history: List[Alert] = []

    async def emit(self, alert_type: str, severity: str, source_feed: str, payload: Dict[str, Any]) -> None:
        alert = Alert(alert_type=alert_type, severity=severity, source_feed=source_feed, timestamp_ms=int(time.time() * 1000), payload=payload)
        self.alert_history.append(alert)
        logger.info({"event": "alert_emitted", "alert_type": alert_type, "severity": severity, "source": source_feed})
        await self.notifier.notify(alert)
