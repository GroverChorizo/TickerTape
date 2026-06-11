from backend.storage import DatasetRegistry
from tui.feeds.hip3 import Hip3Feed
from tui.feeds.smart_money import SmartMoneyFeed


class RecorderClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def get_json(self, endpoint_key: str, **kwargs):
        self.calls.append((endpoint_key, dict(kwargs)))
        return {"ok": True}


def test_smart_money_feed_passes_duration_kwargs(tmp_path):
    client = RecorderClient()
    feed = SmartMoneyFeed(client, registry=DatasetRegistry(path=tmp_path / "_registry.json"))

    payload = feed.fetch()
    assert payload["rankings"] == {"ok": True}

    signal_calls = [kwargs for key, kwargs in client.calls if key == "smart_money_signals"]
    durations = sorted(call.get("duration") for call in signal_calls)
    assert durations == ["10m", "1h", "24h"]


def test_hip3_feed_passes_symbol_and_dex_kwargs(tmp_path):
    client = RecorderClient()
    feed = Hip3Feed(client, registry=DatasetRegistry(path=tmp_path / "_registry.json"))

    payload = feed.fetch()
    assert payload["meta"] == {"ok": True}

    calls = {key: kwargs for key, kwargs in client.calls}
    assert calls["hip3_price"]["symbol"] == "BTC"
    assert calls["hip3_ticks"]["symbol"] == "BTC"
    assert calls["hip3_ticks_dex"]["dex"] == "hl"
    assert calls["hip3_ticks_dex"]["ticker"] == "btc"
