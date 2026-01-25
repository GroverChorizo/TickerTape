import asyncio
import pytest

textual = pytest.importorskip("textual")

from textual.app import App, ComposeResult

from tui.feeds.base import FeedResult
from tui.widgets.event_stream import EventStream
from tui.widgets.funding_panel import FundingPanel
from tui.widgets.market_data_panel import MarketDataPanel
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


def test_market_data_panel_state_transitions():
    panel = MarketDataPanel()
    payload = {
        "selected_coin": "BTC",
        "top_coins": [{"symbol": "BTC", "last": 1.0}],
        "quick": {"best_bid": 1.0, "best_ask": 2.0},
        "orderbook": {"bids": [{"price": 1.0, "size": 1.0}], "asks": [{"price": 2.0, "size": 1.0}]},
        "candles_1h": [{"timestamp_ms": 1, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0}],
        "candles_1m": [{"timestamp_ms": 1, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0}],
    }
    results = [
        FeedResult(status="loading"),
        FeedResult(status="error", error="boom"),
        FeedResult(status="ok", data=payload),
        FeedResult(status="disconnected", data=payload, is_lkg=True),
    ]
    _run_updates(panel, results)


def _panel_text(panel) -> str:
    content = panel.content
    if hasattr(content, "plain"):
        return content.plain
    return str(content)


def test_panel_error_includes_http_status():
    panel = MarketDataPanel()
    result = FeedResult(status="error", error="HTTP 404")

    app = _PanelApp(panel)

    async def _run() -> None:
        async with app.run_test():
            panel.update_feed(result)

    asyncio.run(_run())
    assert "HTTP 404" in _panel_text(panel)
