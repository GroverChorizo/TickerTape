import asyncio
import pytest

textual = pytest.importorskip("textual")

from textual.app import App, ComposeResult

from tui.feeds.base import FeedResult
from tui.widgets.event_stream import EventStream
from tui.widgets.funding_panel import FundingPanel
from tui.widgets.whale_panel import WhalePanel


class _PanelApp(App):
    def __init__(self, panel) -> None:
        super().__init__()
        self._panel = panel

    def compose(self) -> ComposeResult:
        yield self._panel


def _run_updates(panel, results):
    app = _PanelApp(panel)

    async def _run() -> None:
        async with app.run_test():
            for result in results:
                panel.update_feed(result)

    asyncio.run(_run())


def test_funding_panel_state_transitions():
    panel = FundingPanel()
    results = [
        FeedResult(status="loading"),
        FeedResult(status="error", error="boom"),
        FeedResult(status="ok", data={"funding": {"BTC": {"latest": {"rate": 0.0, "timestamp_ms": 1}}}}),
    ]
    _run_updates(panel, results)


def test_whale_panel_disconnect_reconnect():
    panel = WhalePanel()
    lkg_payload = {"trades": [{"symbol": "BTC", "side": "buy", "size": 1, "price": 1, "wallet": "0xabc"}]}
    results = [
        FeedResult(status="disconnected", data=lkg_payload, is_lkg=True),
        FeedResult(status="ok", data=lkg_payload),
    ]
    _run_updates(panel, results)


def test_event_stream_panel_recovery():
    panel = EventStream()
    payload = {"events": [{"timestamp_ms": 1, "symbol": "BTC", "side": "buy", "size": 1}]}
    results = [
        FeedResult(status="loading"),
        FeedResult(status="error", error="boom"),
        FeedResult(status="ok", data=payload),
    ]
    _run_updates(panel, results)


def test_funding_panel_disconnect_lkg():
    panel = FundingPanel()
    payload = {"funding": {"BTC": {"latest": {"rate": 0.0, "timestamp_ms": 1}}}}
    results = [
        FeedResult(status="disconnected", data=payload, is_lkg=True),
        FeedResult(status="ok", data=payload),
    ]
    _run_updates(panel, results)
