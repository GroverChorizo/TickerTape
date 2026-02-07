import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.feeds.market_data import MarketDataFeed, _parse_top_coins


class DummyClient:
    def __init__(self):
        self.calls = []

    def get_json(self, endpoint_key, **kwargs):
        self.calls.append((endpoint_key, kwargs))
        if endpoint_key == "ticks_latest":
            return [
                {"symbol": "BTC", "price": 70000.0, "fundingRateHourly": 0.0001, "openInterestUsd": 123456.0},
                {"symbol": "ETH", "price": 3000.0, "fundingRateHourly": -0.0002, "openInterestUsd": 654321.0},
            ]
        if endpoint_key == "price":
            return {"symbol": "BTC", "price": 70000.0}
        if endpoint_key == "orderbook":
            return {"bids": [[69900, 1.0]], "asks": [[70100, 1.2]]}
        if endpoint_key == "candles":
            return [
                {"t": 1700000000000, "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 10},
            ]
        if endpoint_key == "prices":
            return {"BTC": 70000.0}
        return {}


def test_parse_top_coins_from_ticks():
    raw = [
        {"symbol": "BTC", "price": 70000.0, "fundingRateHourly": 0.0001, "openInterestUsd": 123456.0},
        {"symbol": "ETH", "price": 3000.0, "fundingRateHourly": -0.0002, "openInterestUsd": 654321.0},
    ]
    parsed = _parse_top_coins(raw)
    assert parsed
    assert parsed[0]["symbol"] == "BTC"
    assert parsed[0]["last"] == 70000.0


def test_market_data_feed_uses_ticks_latest():
    client = DummyClient()
    feed = MarketDataFeed(client)
    payload = feed.fetch()
    assert any(call[0] == "ticks_latest" for call in client.calls)
    assert payload.get("top_coins")
