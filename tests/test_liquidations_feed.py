import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from datetime import datetime, timezone, timedelta
from backend.liquidations_feed import LiquidationsFeed
from backend.models import LiquidationEvent


def make_event(ts: datetime, symbol: str, side: str, price: float, size: float, exchange: str = None):
    meta = {"exchange": exchange} if exchange else None
    return LiquidationEvent(timestamp=ts, symbol=symbol, side=side, price=price, size=size, liq_id="x", meta=meta)


def test_compute_snapshot_basic():
    feed = LiquidationsFeed()
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    e1 = make_event(now - timedelta(minutes=30), "BTCUSD", "long", 40000, 1)
    e2 = make_event(now - timedelta(minutes=20), "ETHUSD", "short", 3000, 2)
    e3 = make_event(now - timedelta(minutes=10), "BTCUSD", "long", 41000, 0.5)
    feed.add_event(e1)
    feed.add_event(e2)
    feed.add_event(e3)

    window_start = int((now - timedelta(hours=1)).timestamp() * 1000)
    window_end = int(now.timestamp() * 1000)
    snap = feed.compute_snapshot("1h", window_start, window_end)
    assert snap["count"] == 3
    assert snap["total_notional"] > 0
    assert any(s["symbol"] == "BTCUSD" for s in snap["top_symbols"]) 
