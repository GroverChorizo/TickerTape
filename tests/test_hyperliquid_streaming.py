import asyncio
import json
from pathlib import Path

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


async def _run_streamer(streamer, *, duration: float = 0.1, **start_kwargs):
    streamer.start(**start_kwargs)
    try:
        await asyncio.sleep(duration)
    finally:
        await asyncio.wait_for(streamer.stop(), timeout=1.0)


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
        await _run_streamer(streamer, duration=0.15, poll_interval=0.01)

    asyncio.run(run())

    # Assertions: each feed got at least one push
    assert len(provider._liquidations_feed.payloads) >= 1
    assert len(provider._whales_feed.payloads) >= 1
    assert len(provider._events_feed.payloads) >= 1
    assert len(provider._funding_feed.payloads) >= 1


def test_ws_adapter_publishes_messages_to_feeds():
    async def ws_connect_factory(endpoint_key, **kwargs):
        if endpoint_key == "prices":
            return FakeWS([json.dumps({"tick": {"symbol": "BTC", "px": 43000}})])
        if endpoint_key == "orderbook":
            return FakeWS([json.dumps({"bids": [[43000, 1.2]], "asks": []})])
        if endpoint_key == "info":
            return FakeWS(
                [json.dumps({"funding": {"BTC": {"latest": {"rate": 0.0001}}}})]
            )
        return FakeWS([])

    provider = type("P", (), {})()
    provider._client = type("C", (), {})()
    provider._client.ws_connect = ws_connect_factory

    provider._market_feed = DummyFeed()
    provider._liquidations_feed = DummyFeed()
    provider._funding_feed = DummyFeed()

    async def run():
        streamer = HyperliquidStreamer(provider)
        await _run_streamer(streamer, duration=0.12, poll_interval=0.01)

    asyncio.run(run())

    assert any(isinstance(p, dict) for p in provider._market_feed.payloads)
    assert len(provider._funding_feed.payloads) >= 1


def test_ticks_stream_pushes_to_market_feed():
    async def ws_connect_factory(endpoint_key, **kwargs):
        if endpoint_key == "ticks_latest":
            return FakeWS([json.dumps({"symbol": "BTC", "price": 43000})])
        return FakeWS([])

    provider = type("P", (), {})()
    provider._client = type("C", (), {})()
    provider._client.ws_connect = ws_connect_factory
    provider._market_feed = DummyFeed()

    async def run():
        streamer = HyperliquidStreamer(provider)
        await _run_streamer(streamer, duration=0.06, poll_interval=0.01)

    asyncio.run(run())

    assert any(isinstance(p, dict) for p in provider._market_feed.payloads)


def test_market_throttling_limits_pushes():
    """When market_max_hz is set, ensure we don't push more than the rate allows."""

    async def ws_connect_factory(endpoint_key, **kwargs):
        class FastWS(FakeWS):
            def __init__(self, n):
                self._count = n

            async def __anext__(self):
                if self._count <= 0:
                    raise StopAsyncIteration
                self._count -= 1
                await asyncio.sleep(0)
                return json.dumps({"tick": {"symbol": "BTC", "px": 43000}})

        if endpoint_key == "ticks_latest":
            # produce many ticks in the same loop cycle
            return FastWS(20)
        return FastWS(0)

    provider = type("P", (), {})()
    provider._client = type("C", (), {})()
    provider._client.ws_connect = ws_connect_factory
    provider._market_feed = DummyFeed()

    async def run():
        streamer = HyperliquidStreamer(provider)
        await _run_streamer(
            streamer, duration=0.25, poll_interval=0.001, market_agg_ms=0, market_max_hz=5
        )

    asyncio.run(run())

    pushes = len(provider._market_feed.payloads)
    duration = 0.25
    allowed = max(1, int(duration * 5) + 3)  # allow small scheduling jitter
    assert pushes <= allowed, f"got too many pushes: {pushes} (expected <= {allowed})"


def test_binance_funding_stream_parsed_and_pushed():
    async def ws_connect_factory(endpoint_key, **kwargs):
        if endpoint_key == "binance_funding":
            return FakeWS([json.dumps({"BTC": {"latest": {"rate": 0.00012}}})])
        return FakeWS([])

    provider = type("P", (), {})()
    provider._client = type("C", (), {})()
    provider._client.ws_connect = ws_connect_factory
    provider._funding_feed = DummyFeed()

    async def run():
        streamer = HyperliquidStreamer(provider)
        await _run_streamer(streamer, duration=0.05, poll_interval=0.01)

    asyncio.run(run())

    assert len(provider._funding_feed.payloads) >= 1
    assert isinstance(provider._funding_feed.payloads[0], dict)


def test_market_aggregation_uses_last_tick_from_fixture():
    fixture_path = Path(__file__).parent / "fixtures" / "ws_prices.jsonl"

    async def ws_connect_factory(endpoint_key, **kwargs):
        lines = fixture_path.read_text(encoding="utf-8").splitlines()
        if endpoint_key == "prices":
            # after the fixture lines are exhausted, keep the connection open so the
            # supervisor does not immediately reconnect and replay the fixture.
            class LiveFakeWS(FakeWS):
                async def __anext__(self):
                    try:
                        return next(self._it)
                    except StopIteration:
                        await asyncio.Event().wait()

            return LiveFakeWS(lines)
        return FakeWS([])

    provider = type("P", (), {})()
    provider._client = type("C", (), {})()
    provider._client.ws_connect = ws_connect_factory
    provider._market_feed = DummyFeed()

    async def run():
        streamer = HyperliquidStreamer(provider)
        await _run_streamer(streamer, duration=0.14, poll_interval=0.01, market_agg_ms=50)

    asyncio.run(run())

    # fixture had 3 rapid ticks; after aggregation we expect 1 push
    assert provider._market_feed.payloads
    assert len(provider._market_feed.payloads) == 1
    p = provider._market_feed.payloads[0]
    assert isinstance(p, dict)
    assert p.get("tick", {}).get("px") == 43002.0


def test_orderbook_replay_parses_and_pushes():
    fixture_path = Path(__file__).parent / "fixtures" / "ws_orderbook.jsonl"

    async def ws_connect_factory(endpoint_key, **kwargs):
        lines = fixture_path.read_text(encoding="utf-8").splitlines()
        return FakeWS(lines)

    provider = type("P", (), {})()
    provider._client = type("C", (), {})()
    provider._client.ws_connect = ws_connect_factory
    provider._market_feed = DummyFeed()

    async def run():
        streamer = HyperliquidStreamer(provider)
        await _run_streamer(streamer, duration=0.12, poll_interval=0.01, market_agg_ms=50)

    asyncio.run(run())

    assert len(provider._market_feed.payloads) == 1
    p = provider._market_feed.payloads[0]
    assert isinstance(p, dict)
    assert "bids" in p and "asks" in p


def test_streamer_exposes_per_endpoint_stats():
    async def ws_connect_factory(endpoint_key, **kwargs):
        # First connection for orderbook fails, then succeeds.
        if endpoint_key == "orderbook":
            ws_connect_factory.calls += 1
            if ws_connect_factory.calls == 1:
                raise RuntimeError("boom")
            return FakeWS([json.dumps({"bids": [[43000, 1]], "asks": [[43010, 1]]})])
        if endpoint_key == "ticks_latest":
            return FakeWS([json.dumps({"symbol": "BTC", "price": 43000})])
        return FakeWS([])

    ws_connect_factory.calls = 0

    provider = type("P", (), {})()
    provider._client = type("C", (), {})()
    provider._client.ws_connect = ws_connect_factory
    provider._market_feed = DummyFeed()
    provider._liquidations_feed = DummyFeed()
    provider._whales_feed = DummyFeed()
    provider._events_feed = DummyFeed()
    provider._funding_feed = DummyFeed()

    async def run():
        streamer = HyperliquidStreamer(provider)
        streamer.start(poll_interval=0.01)
        await asyncio.sleep(0.15)
        stats = streamer.stats()
        await asyncio.wait_for(streamer.stop(), timeout=1.0)
        assert "orderbook" in stats
        assert stats["orderbook"]["error_count"] >= 1
        assert stats["orderbook"]["reconnect_count"] >= 0
        assert "ticks_latest" in stats
        assert stats["ticks_latest"]["messages_received"] >= 1
        assert stats["ticks_latest"]["lag_ms"] is not None

    asyncio.run(run())
