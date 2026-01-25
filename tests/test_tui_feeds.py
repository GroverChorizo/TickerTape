from tui.feeds.base import BaseFeed, FeedResult
from tui.feeds.hyperliquid import FundingRatesFeed, _parse_funding_history
from backend.storage import DatasetRegistry
from backend import storage


class DummyFeed(BaseFeed):
    def __init__(self, payloads):
        super().__init__(name="dummy", poll_interval=0.01)
        self._payloads = list(payloads)

    def fetch(self):
        if not self._payloads:
            return {}
        value = self._payloads.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


def test_base_feed_caches_last_known_good():
    feed = DummyFeed([{"value": 1}, {}])
    first = feed.fetch_result()
    assert first.status == "ok"
    second = feed.fetch_result()
    assert second.status == "empty"
    assert second.data == {"value": 1}


def test_base_feed_handles_disconnect():
    feed = DummyFeed([TimeoutError("boom")])
    result = feed.fetch_result()
    assert result.status == "disconnected"


def test_parse_funding_history_minimal_schema():
    raw = [
        {"time": 1700000000000, "fundingRate": 0.0},
        {"timestamp_ms": 1700000060000, "fundingRate": -0.0001},
    ]
    points = _parse_funding_history(raw)
    assert len(points) == 2
    assert points[0].timestamp_ms == 1700000000000


def test_parse_funding_history_handles_invalid_payload():
    points = _parse_funding_history({"bad": "payload"})
    assert points == []


def test_funding_feed_persists_snapshot(tmp_path, monkeypatch):
    class DummyClient:
        def post(self, endpoint_key, payload):
            return [
                {"time": 1700000000000, "fundingRate": 0.0},
                {"timestamp_ms": 1700000060000, "fundingRate": -0.0001},
            ]

    parquet_root = tmp_path / "parquet"
    monkeypatch.setattr(storage, "BASE_PARQUET_ROOT", parquet_root)
    registry = DatasetRegistry(path=tmp_path / "registry.json")
    feed = FundingRatesFeed(DummyClient(), coins=["BTC"], registry=registry)
    payload = feed.fetch()
    assert "funding" in payload

    datasets = registry.list_datasets()
    assert "feed=funding_rates" in datasets
    parts = datasets["feed=funding_rates"]["partitions"]
    assert parts
    stored_path = parquet_root / parts[0]
    assert stored_path.exists() or stored_path.with_suffix(stored_path.suffix + ".ndjson").exists()
