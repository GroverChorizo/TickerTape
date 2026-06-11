"""Status bar with screen status, health indicators, and breadcrumb."""

from __future__ import annotations

from typing import Any

from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static


class StatusBar(Vertical):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.status_line = Static("", id="status_line")
        self.health_line = Static("", id="health_line")
        self.diagnostics_button = Button("Diagnostics", id="status_diagnostics")
        self.alerts_button = Button("Alerts", id="status_alerts")
        self.breadcrumb_line = Static("", id="breadcrumb_line")

    def compose(self):
        yield self.status_line
        with Horizontal(id="status_health_row"):
            yield self.health_line
            yield self.diagnostics_button
            yield self.alerts_button
        yield self.breadcrumb_line

    def set_status(self, text: str) -> None:
        self.status_line.update(text)

    def set_health(self, snapshot: dict[str, Any]) -> None:
        connection = str(snapshot.get("connection", "unknown")).upper()
        api_state = str(snapshot.get("api_state", "unknown")).upper()
        latency = snapshot.get("api_latency_ms")
        ws_live = int(snapshot.get("ws_live", 0))
        ws_total = int(snapshot.get("ws_total", 0))
        freshness_ms = snapshot.get("freshness_ms")
        bandwidth_msg_s = float(snapshot.get("bandwidth_msg_s", 0.0))
        alerts = int(snapshot.get("alert_count", 0))
        muted = bool(snapshot.get("alert_muted", False))
        latency_text = (
            f"{float(latency):.1f}ms" if isinstance(latency, (int, float)) else "n/a"
        )
        if isinstance(freshness_ms, (int, float)):
            freshness_text = f"{max(0, int(freshness_ms)) // 1000}s"
        else:
            freshness_text = "n/a"
        alerts_text = f"{alerts}{' (muted)' if muted else ''}"
        ws_degraded = ws_live < ws_total
        ws_reconnecting = str(snapshot.get("ws_reconnecting", False)) in {"True", "1", "true"}
        if ws_reconnecting:
            ws_text = f"WS {ws_live}/{ws_total} ↻"
        elif ws_degraded:
            ws_text = f"WS {ws_live}/{ws_total} !"
        else:
            ws_text = f"WS {ws_live}/{ws_total}"
        from rich.text import Text as _Text
        health = _Text()
        health.append(f"CONN {connection} | API {api_state} {latency_text} | ")
        if ws_reconnecting:
            health.append(ws_text, style="bold yellow")
        elif ws_degraded:
            health.append(ws_text, style="bold red")
        else:
            health.append(ws_text)
        health.append(
            f" | Fresh {freshness_text} | BW {bandwidth_msg_s:.1f} msg/s | Alerts {alerts_text}"
        )
        health.append(" | NOT FINANCIAL ADVICE", style="dim")
        self.health_line.update(health)

    def set_breadcrumb(self, text: str) -> None:
        self.breadcrumb_line.update(text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "status_diagnostics":
            self._dispatch_command("diagnostics")
            event.stop()
            return
        if event.button.id == "status_alerts":
            self._dispatch_command("alerts")
            event.stop()

    def _dispatch_command(self, command: str) -> None:
        app = getattr(self, "app", None)
        if app is None:
            return
        dispatch = getattr(app, "dispatch_command", None)
        if callable(dispatch):
            context = getattr(getattr(app, "screen", None), "command_context", "home")
            dispatch(command, context=context)
