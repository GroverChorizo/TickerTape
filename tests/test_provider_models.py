from __future__ import annotations

from providers.models import (
    FundingRate,
    LiquidationEvent,
    OrderBookLevel,
    OrderBookSnapshot,
    Position,
    Tick,
    WhaleTrade,
)


def test_provider_models_construct():
    tick = Tick(ts_ms=1, symbol="BTC", price=100.0)
    assert tick.symbol == "BTC"

    bids = [OrderBookLevel(price=99.0, size=1.0)]
    asks = [OrderBookLevel(price=101.0, size=2.0)]
    book = OrderBookSnapshot(ts_ms=2, symbol="BTC", bids=bids, asks=asks)
    assert book.bids[0].price == 99.0

    liq = LiquidationEvent(ts_ms=3, symbol="ETH", side="long_liq", notional_usd=500.0)
    assert liq.notional_usd == 500.0

    whale = WhaleTrade(ts_ms=4, symbol="SOL", side="buy", notional_usd=1000.0)
    assert whale.symbol == "SOL"

    rate = FundingRate(ts_ms=5, symbol="BTC", rate=0.001)
    assert rate.rate == 0.001

    pos = Position(ts_ms=6, symbol="BTC", side="long", size=1.0)
    assert pos.size == 1.0
