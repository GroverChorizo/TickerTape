import asyncio
import json
from pathlib import Path

from providers.hyperliquid import HyperliquidProvider


class FakeWS:
    def __init__(self, messages):
        self._it = iter(messages)

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


async def _first(async_iter, *, timeout: float = 0.5):
    try:
        item = await asyncio.wait_for(async_iter.__anext__(), timeout=timeout)
    finally:
        await async_iter.aclose()
    return item


def test_stream_orderbook_parses_ws_fixture():
    lines = (Path(__file__).parent / "fixtures" / "ws_orderbook.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()

    class DummyClient:
        async def ws_connect(self, endpoint_key, **_kwargs):
            assert endpoint_key == "orderbook"
            return FakeWS(lines)

    provider = HyperliquidProvider(
        client=DummyClient(),
        stream_min_backoff=0.0,
        stream_max_backoff=0.0,
    )

    async def run():
        snapshot = await _first(provider.stream_orderbook("BTC"))
        assert snapshot.symbol == "BTC"
        assert snapshot.bids
        assert snapshot.asks

    asyncio.run(run())


def test_stream_funding_rates_from_ws_fixture():
    lines = (Path(__file__).parent / "fixtures" / "ws_funding.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()

    class DummyClient:
        async def ws_connect(self, endpoint_key, **_kwargs):
            assert endpoint_key == "funding"
            return FakeWS(lines)

    provider = HyperliquidProvider(
        client=DummyClient(),
        stream_min_backoff=0.0,
        stream_max_backoff=0.0,
    )

    async def run():
        rate = await _first(provider.stream_funding_rates())
        assert rate.symbol in {"BTC", "ETH"}
        assert rate.rate > 0

    asyncio.run(run())


def test_stream_reconnects_after_failure():
    payload = json.dumps({"bids": [[1, 1]], "asks": [], "symbol": "BTC"})

    class DummyClient:
        def __init__(self):
            self.calls = 0

        async def ws_connect(self, endpoint_key, **_kwargs):
            assert endpoint_key == "orderbook"
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("boom")
            return FakeWS([payload])

    client = DummyClient()
    provider = HyperliquidProvider(
        client=client,
        stream_min_backoff=0.0,
        stream_max_backoff=0.0,
    )

    async def run():
        snapshot = await _first(provider.stream_orderbook("BTC"), timeout=0.8)
        assert snapshot.symbol == "BTC"
        assert client.calls >= 2

    asyncio.run(run())
