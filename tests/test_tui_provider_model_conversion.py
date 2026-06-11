from backend.storage import DatasetRegistry
from tui.models.liquidations import LiquidationSnapshot
from tui.models.market import MarketContext
from tui.providers.hyperliquid import HyperliquidProvider


class DummyClient:
    def get_json(self, endpoint_key: str, **kwargs):
        if endpoint_key == "ticks_latest":
            return {
                "data": [
                    {
                        "symbol": "BTC",
                        "price": 100.0,
                        "funding": 0.001,
                        "open_interest": 12345.0,
                    }
                ]
            }
        if endpoint_key == "price":
            return {"best_bid": 99.0, "best_ask": 101.0, "mid": 100.0, "spread": 2.0}
        if endpoint_key == "orderbook":
            return {"bids": [[99.0, 1.0]], "asks": [[101.0, 1.2]]}
        if endpoint_key == "candles":
            return [{"t": 1, "o": 1, "h": 1, "l": 1, "c": 1, "v": 1}]
        return {}

    def close(self) -> None:
        return None


def test_provider_converts_market_and_liquidation_payloads(tmp_path):
    provider = HyperliquidProvider(
        client=DummyClient(),
        registry=DatasetRegistry(path=tmp_path / "_registry.json"),
    )

    market = provider.get_market_context("BTC")
    assert market.status == "ok"
    assert isinstance(market.data, MarketContext)
    assert market.data.symbol == "BTC"

    liquidations = provider.get_liquidations()
    assert liquidations.status in {"ok", "empty"}
    assert isinstance(liquidations.data, LiquidationSnapshot)
