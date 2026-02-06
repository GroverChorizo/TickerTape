import asyncio

import pytest

from tui.feeds.moondev_client import MoonDevClient


class _FakeWS:
    def __init__(self, msgs, record):
        self._it = iter(msgs)
        self.record = record

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


def test_ws_connect_uses_websocket_scheme_and_injects_header(monkeypatch):
    captured = {}

    async def fake_connect(url, **kwargs):
        # record call and return a fake ws context
        captured["url"] = url
        captured.update(kwargs)
        return _FakeWS(["{\"tick\":{\"px\":123}}"], captured)

    # Ensure resolve_moondev_api_key returns a known key
    monkeypatch.setattr(
        "tui.feeds.moondev_client.resolve_moondev_api_key",
        lambda: ("TESTKEY", "env"),
    )
    # Inject our fake `websockets` module so the inner import resolves to our fake
    import sys

    fake_mod = type("M", (), {"connect": staticmethod(fake_connect)})
    monkeypatch.setitem(sys.modules, "websockets", fake_mod)

    client = MoonDevClient(base_url="https://api.moondev.com")

    async def run():
        async with await client.ws_connect("prices") as ws:
            async for msg in ws:
                assert "tick" in msg
                break

    asyncio.run(run())

    assert captured["url"].startswith("wss://")
    # header should be passed via extra_headers or extra kwargs (websockets API varies)
    assert any("TESTKEY" in str(v) for v in captured.values())


def test_ws_connect_retries_with_query_param_on_error(monkeypatch):
    calls = []

    async def failing_connect(url, **kwargs):
        calls.append(url)
        raise RuntimeError("handshake failed")

    async def working_connect(url, **kwargs):
        calls.append(url)
        return _FakeWS(["{\"ok\":true}\n"], {})

    monkeypatch.setattr(
        "tui.feeds.moondev_client.resolve_moondev_api_key",
        lambda: ("QK", "env"),
    )

    # websockets.connect will raise first, then succeed
    class _W:
        _first = True

        @staticmethod
        async def connect(url, **kwargs):
            if _W._first:
                _W._first = False
                return await failing_connect(url, **kwargs)
            return await working_connect(url, **kwargs)

    import sys
    monkeypatch.setitem(sys.modules, "websockets", _W)

    client = MoonDevClient(base_url="https://api.moondev.com/v1")

    async def run():
        # should not raise even though first handshake failed (fallback path)
        async with await client.ws_connect("binance_funding") as ws:
            async for _ in ws:
                break

    asyncio.run(run())

    assert any("api_key=QK" in c for c in calls)
