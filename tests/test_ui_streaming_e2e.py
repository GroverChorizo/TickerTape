import asyncio
import json

from tui.providers.hyperliquid import HyperliquidStreamer
from tui.ui.widgets.orderbook_imbalance import OrderbookImbalanceWidget


class DummyFeed:
    def __init__(self):
        self.payloads = []

    def push(self, payload):
        self.payloads.append(payload)


async def _ws_factory_for_all(endpoint_key, **kwargs):
    class FakeWS:
        def __init__(self, msgs):
            self._it = iter(msgs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def __aiter__(self):
            return self

        async def __anext__(self):
            await asyncio.sleep(0)
            try:
                return next(self._it)
            except StopIteration:
                raise StopAsyncIteration

    if endpoint_key in ("prices", "ticks_latest"):
        return FakeWS([json.dumps({"tick": {"symbol": "BTC", "px": 43000}})])
    if endpoint_key == "orderbook":
        return FakeWS([json.dumps({"bids": [[43000, 1.2]], "asks": [[43010, 0.8]]})])
    if endpoint_key == "info":
        return FakeWS([json.dumps({"funding": {"BTC": {"latest": {"rate": 0.00012}}}})])
    return FakeWS([])

async def _run_streamer(streamer, *, duration: float = 0.05, **start_kwargs):
    streamer.start(**start_kwargs)
    try:
        await asyncio.sleep(duration)
    finally:
        await asyncio.wait_for(streamer.stop(), timeout=1.0)


def test_e2e_streams_update_feeds_and_widget():
    provider = type("P", (), {})()
    provider._client = type("C", (), {})()
    provider._client.ws_connect = _ws_factory_for_all

    # install feeds expected by streamer
    provider._market_feed = DummyFeed()
    provider._funding_feed = DummyFeed()
    provider._liquidations_feed = DummyFeed()

    streamer = HyperliquidStreamer(provider)
    asyncio.run(_run_streamer(streamer, duration=0.05, poll_interval=0.01, market_agg_ms=0))

    # market feed received pushed payloads (funding is keyless now and no
    # longer streamed through the supervisor)
    assert any(isinstance(p, dict) for p in provider._market_feed.payloads)

    # widget should render from the latest orderbook payload
    w = OrderbookImbalanceWidget()
    # reuse last market payload (orderbook)
    orderbook = next((p for p in provider._market_feed.payloads if p and p.get("bids")), None)
    assert orderbook is not None
    w.update_from_orderbook(orderbook)
    panel = w.render()
    assert hasattr(panel, "title") and "Orderbook Imbalance" in (panel.title or "")
    from rich.console import Console

    console = Console(record=True, width=80)
    console.print(panel)
    out = console.export_text()
    assert "Bids" in out and "Asks" in out
