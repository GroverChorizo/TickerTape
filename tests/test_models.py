import pytest
from datetime import datetime, timezone
from backend.models import TradeEvent, LiquidationEvent, FundingEvent, Candle


def test_trade_event_validation():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        TradeEvent(timestamp=now, symbol="BTCUSD", side="buy", price=-1.0, size=1.0, trade_id="t1")
    with pytest.raises(ValueError):
        TradeEvent(timestamp=now, symbol="BTCUSD", side="buy", price=1.0, size=0.0, trade_id="t2")

    t = TradeEvent(timestamp=now, symbol="BTCUSD", side="sell", price=1.0, size=1.0, trade_id="t3")
    d = t.to_dict()
    assert d["symbol"] == "BTCUSD"


def test_candle_validation():
    now = datetime.now(timezone.utc)
    # invalid high/low
    with pytest.raises(ValueError):
        Candle(timestamp=now, symbol="BTCUSD", open=10, high=9, low=5, close=8, volume=1)
    # negative volume
    with pytest.raises(ValueError):
        Candle(timestamp=now, symbol="BTCUSD", open=10, high=12, low=8, close=11, volume=-1)

    c = Candle(timestamp=now, symbol="BTCUSD", open=10, high=12, low=8, close=11, volume=0)
    assert c.volume == 0