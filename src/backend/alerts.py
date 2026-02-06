"""AlertManager and simple TCP notifier for frontend consumption.

- Alert messages are JSON lines sent to connected TCP clients (host/port configurable)
- Alert schema: alert_type, severity, source_feed, timestamp_ms, payload
"""

from __future__ import annotations
import asyncio
import json
from dataclasses import asdict
from typing import Any, Dict, List, Optional
import logging
import time

from tickertape.core.alerts import AlertEvent, AlertSeverity, AlertService

logger = logging.getLogger(__name__)

Alert = AlertEvent


class SocketNotifier:
    """Simple TCP server that broadcasts JSON alert messages to connected clients.

    Designed for local development and testing (frontend can connect via localhost).
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self._server: Optional[asyncio.AbstractServer] = None
        self._clients: List[asyncio.StreamWriter] = []

    async def _handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
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
        logger.info(
            {"event": "socket_notifier_started", "host": self.host, "port": self.port}
        )

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

    async def notify(self, alert: AlertEvent) -> None:
        msg = _alert_to_json(alert) + "\n"
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


class AlertManager(AlertService):
    def __init__(self, notifier: SocketNotifier) -> None:
        self.notifier = notifier
        self.alert_history: List[AlertEvent] = []

    async def emit(
        self,
        alert: AlertEvent | str,
        severity: str | AlertSeverity | None = None,
        source_feed: str | None = None,
        payload: Dict[str, Any] | None = None,
    ) -> None:
        """Emit an alert.

        Accepts either a fully-formed AlertEvent or legacy parts for compatibility.
        """
        if isinstance(alert, AlertEvent):
            event = alert
        else:
            event = AlertEvent(
                alert_type=alert,
                severity=_coerce_severity(severity or AlertSeverity.INFO),
                source_feed=source_feed or "unknown",
                timestamp_ms=int(time.time() * 1000),
                payload=payload or {},
            )
        self.alert_history.append(event)
        logger.info(
            {
                "event": "alert_emitted",
                "alert_type": event.alert_type,
                "severity": event.severity.value,
                "source": event.source_feed,
            }
        )
        await self.notifier.notify(event)

    async def emit_from_parts(
        self,
        alert_type: str,
        severity: str | AlertSeverity,
        source_feed: str,
        payload: Dict[str, Any],
    ) -> None:
        await self.emit(alert_type, severity, source_feed, payload)


def _coerce_severity(value: str | AlertSeverity) -> AlertSeverity:
    if isinstance(value, AlertSeverity):
        return value
    try:
        return AlertSeverity(value)
    except Exception:
        return AlertSeverity.INFO


def _alert_to_json(alert: AlertEvent) -> str:
    payload = asdict(alert)
    payload["severity"] = alert.severity.value
    return json.dumps(payload, separators=(",", ":"))
