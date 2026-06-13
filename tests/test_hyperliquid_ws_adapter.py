import asyncio

from tui.providers.hyperliquid import HyperliquidStreamer


class FakeAsyncIter:
    def __init__(self, seq):
        self._seq = list(seq)
        self._i = 0
        self._closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._closed = True
        return False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._closed or self._i >= len(self._seq):
            raise StopAsyncIteration
        v = self._seq[self._i]
        self._i += 1
        await asyncio.sleep(0)
        return v


class DummyClient:
    def __init__(self, frames_map):
        self._frames = {k: list(v) for k, v in frames_map.items()}

    async def ws_connect(self, endpoint_key: str, **kwargs):
        frames = self._frames.get(endpoint_key, [])
        return FakeAsyncIter(frames)


class DummyFeed:
    def __init__(self):
        self.payloads = []

    def push(self, payload):
        self.payloads.append(payload)


def test_ws_adapter_prioritized_and_pushes():
    client = DummyClient(
        {
            "prices": [{"price": 100}],
            "orderbook": [{"bids": []}],
            "hip3_ticks_dex": [[{"t": 1}]],
            "info": [{"funding": {"BTC": {"latest": {}}}}],
        }
    )

    provider = type("P", (), {})()
    provider._client = client
    provider._liquidations_feed = DummyFeed()
    provider._market_feed = DummyFeed()
    provider._whales_feed = DummyFeed()
    provider._events_feed = DummyFeed()
    provider._funding_feed = DummyFeed()

    async def run():
        streamer = HyperliquidStreamer(provider)
        streamer.start(poll_interval=0.01)
        try:
            await asyncio.sleep(0.1)
        finally:
            await asyncio.wait_for(streamer.stop(), timeout=1.0)

    asyncio.run(run())

    # core market streaming still pushes (funding is keyless now and no longer
    # streamed through the supervisor)
    assert provider._market_feed.payloads
