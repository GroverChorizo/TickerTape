import asyncio

import pytest

textual = pytest.importorskip("textual")

from textual.app import App

from tui.ui.status_bar import StatusBar


class _StatusBarHostApp(App):
    def __init__(self) -> None:
        super().__init__()
        self.dispatched: list[tuple[str, str]] = []

    def compose(self):
        yield StatusBar(id="status_bar")

    def dispatch_command(self, raw: str, *, context: str) -> None:
        self.dispatched.append((raw, context))


def test_status_bar_formats_health_and_buttons_dispatch():
    app = _StatusBarHostApp()

    async def _run() -> None:
        async with app.run_test(size=(140, 24)) as pilot:
            bar = app.query_one(StatusBar)
            setattr(app.screen, "command_context", "day_trader")
            bar.set_health(
                {
                    "connection": "live",
                    "api_state": "ok",
                    "api_latency_ms": 12.4,
                    "ws_live": 3,
                    "ws_total": 5,
                    "freshness_ms": 3200,
                    "bandwidth_msg_s": 9.8,
                    "alert_count": 7,
                    "alert_muted": True,
                }
            )
            await pilot.pause()
            rendered = str(bar.health_line.renderable)
            assert "CONN LIVE" in rendered
            assert "API OK 12.4ms" in rendered
            assert "WS 3/5" in rendered
            assert "Fresh 3s" in rendered
            assert "BW 9.8 msg/s" in rendered
            assert "Alerts 7 (muted)" in rendered

            bar.diagnostics_button.press()
            await pilot.pause()
            bar.alerts_button.press()
            await pilot.pause()

    asyncio.run(_run())
    assert app.dispatched == [
        ("diagnostics", "day_trader"),
        ("alerts", "day_trader"),
    ]
