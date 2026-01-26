from tui.feeds.market_data import (
    MarketDataFeed,
    _parse_candles,
    _parse_top_coins,
)


class DummyClient:
    def __init__(self, responses):
        self.responses = responses

    def get_json(self, endpoint_key, params=None, **kwargs):
        key = (endpoint_key, tuple(sorted(kwargs.items())))
        if params:
            key = (endpoint_key, tuple(sorted(kwargs.items())), tuple(sorted(params.items())))
        value = self.responses[key]
        if isinstance(value, list):
            if not value:
                raise RuntimeError("no response queued")
            value = value.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


def test_parse_top_coins_minimal_schema():
    raw = [
        {"symbol": "BTC", "price": 1, "fundingRate": 0.0, "openInterest": 2, "timestamp": 1},
    ]
    parsed = _parse_top_coins(raw)
    assert parsed[0]["symbol"] == "BTC"
    assert parsed[0]["last"] == 1.0


def test_parse_candles_minimal_schema():
    raw = [
        {"t": 1, "o": 1, "h": 1, "l": 1, "c": 1, "v": 1},
    ]
    parsed = _parse_candles(raw)
    assert parsed[0]["timestamp_ms"] == 1


def test_market_data_feed_disconnect_and_recovery():
    responses = {
        ("prices", ()): [{"symbol": "BTC", "price": 1}],
        ("price", (("symbol", "BTC"),)): {"bestBid": 1, "bestAsk": 2},
        ("orderbook", (("symbol", "BTC"),)): {"bids": [[1, 1]], "asks": [[2, 1]]},
        ("candles", (("symbol", "BTC"),), (("interval", "1h"), ("limit", 10))): [{"t": 1, "o": 1, "h": 1, "l": 1, "c": 1}],
        ("candles", (("symbol", "BTC"),), (("interval", "1m"), ("limit", 10))): [{"t": 1, "o": 1, "h": 1, "l": 1, "c": 1}],
    }
    client = DummyClient(responses)
    feed = MarketDataFeed(client)
    first = feed.fetch_result()
    assert first.status == "ok"

    error = ConnectionError("offline")
    for key in list(responses.keys()):
        responses[key] = error
    feed._last_fetch = {k: 0.0 for k in feed._last_fetch}
    disconnected = feed.fetch_result()
    assert disconnected.status == "disconnected"
    assert disconnected.data is not None

    responses[("prices", ())] = [{"symbol": "BTC", "price": 2}]
    responses[("price", (("symbol", "BTC"),))] = {"bestBid": 2, "bestAsk": 3}
    responses[("orderbook", (("symbol", "BTC"),))] = {"bids": [[2, 1]], "asks": [[3, 1]]}
    responses[("candles", (("symbol", "BTC"),), (("interval", "1h"), ("limit", 10)))] = [{"t": 2, "o": 2, "h": 2, "l": 2, "c": 2}]
    responses[("candles", (("symbol", "BTC"),), (("interval", "1m"), ("limit", 10)))] = [{"t": 2, "o": 2, "h": 2, "l": 2, "c": 2}]
    feed._last_fetch = {k: 0.0 for k in feed._last_fetch}
    recovered = feed.fetch_result()
    assert recovered.status == "ok"
