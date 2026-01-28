import asyncio
import time

from tui.providers.hyperliquid import HyperliquidStreamer


class DummyFeed:
    def __init__(self):
        self.payloads = []

    def push(self, payload):
        self.payloads.append(payload)


class DummyClient:
    def __init__(self, mapping):
        # mapping: endpoint_key -> list of responses
        self.mapping = {k: list(v) for k, v in mapping.items()}

    def get_json(self, endpoint_key, **kwargs):
        lst = self.mapping.get(endpoint_key)
        if not lst:
            return {}
        return lst.pop(0)


def test_hyperliquid_streamer_pushes_to_feeds():
    client = DummyClient(
        {
            "liquidations": [{"events": [1]}, {"events": [2]}],
            "whales": [[{"trade": "a"}]],
            "events": [[{"e": 1}]],
            "info": [{"funding": {"BTC": {"latest": {}}}}],
        }
    )
    provider = type("P", (), {})()
    provider._client = client
    provider._liquidations_feed = DummyFeed()
    provider._whales_feed = DummyFeed()
    provider._events_feed = DummyFeed()
    provider._funding_feed = DummyFeed()

    async def run():
        streamer = HyperliquidStreamer(provider)
        streamer.start(poll_interval=0.01)
        # allow a few short poll cycles
        await asyncio.sleep(0.15)
        await streamer.stop()

    asyncio.run(run())

    # Assertions: each feed got at least one push
    assert len(provider._liquidations_feed.payloads) >= 1
    assert len(provider._whales_feed.payloads) >= 1
    assert len(provider._events_feed.payloads) >= 1
    assert len(provider._funding_feed.payloads) >= 1
