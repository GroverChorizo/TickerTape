from backend.storage import DatasetRegistry
from tui.providers.hyperliquid import HyperliquidProvider


class DummyClient:
    def get_json(self, *_args, **_kwargs):
        raise RuntimeError("boom")


def test_hyperliquid_provider_errors(tmp_path):
    registry = DatasetRegistry(path=tmp_path / "_registry.json")
    provider = HyperliquidProvider(client=DummyClient(), registry=registry)

    liq_result = provider.get_liquidations()
    assert liq_result.status == "error"
    assert "boom" in (liq_result.error or "")

    market_result = provider.get_market_context("BTC")
    assert market_result.status == "error"
