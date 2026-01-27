from __future__ import annotations

from providers.hyperliquid import HyperliquidProvider


class DummyClient:
    def __init__(self) -> None:
        self.calls = 0

    def get_json(self, *_args, **_kwargs):
        self.calls += 1
        return {
            "events": [
                {
                    "timestamp_ms": 1,
                    "symbol": "BTC",
                    "side": "long",
                    "value_usd": 1000,
                }
            ]
        }

    def close(self) -> None:
        pass


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value


def test_liquidations_cached_within_ttl():
    clock = FakeClock()
    client = DummyClient()
    provider = HyperliquidProvider(client=client, cache_ttl_s=10.0, now_fn=clock)

    first = provider.get_liquidations()
    assert client.calls == 1
    assert first[0].symbol == "BTC"

    clock.value = 5.0
    second = provider.get_liquidations()
    assert client.calls == 1
    assert second[0].symbol == "BTC"

    clock.value = 11.0
    third = provider.get_liquidations()
    assert client.calls == 2
    assert third[0].symbol == "BTC"
