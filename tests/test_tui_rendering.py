import asyncio
import pytest

pytest.importorskip("textual")
pytest.importorskip("httpx")


textual = pytest.importorskip("textual")

from textual.app import App, ComposeResult

from tui.widgets.liquidations_panel import LiquidationsPanel
from tui.feeds.base import FeedResult


class _TestApp(App):
    def __init__(self, panel: LiquidationsPanel) -> None:
        super().__init__()
        self._panel = panel

    def compose(self) -> ComposeResult:
        yield self._panel


def test_liquidations_panel_handles_empty_payload():
    panel = LiquidationsPanel()
    app = _TestApp(panel)

    async def _run() -> None:
        async with app.run_test():
            panel.update_feed(FeedResult(status="empty", data=None))

    asyncio.run(_run())


def test_liquidations_panel_handles_disconnected_lkg():
    panel = LiquidationsPanel()
    app = _TestApp(panel)
    payload = {
        "snapshot": {"total_notional": 1000000, "count": 5, "cascade_detected": False}
    }

    async def _run() -> None:
        async with app.run_test():
            panel.update_feed(
                FeedResult(status="disconnected", data=payload, is_lkg=True)
            )

    asyncio.run(_run())
