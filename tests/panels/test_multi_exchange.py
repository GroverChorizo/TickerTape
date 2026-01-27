import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.config import update_funding_exchanges
from tui.feeds.funding import FundingRow, detect_arbitrage


def test_detect_arbitrage_flags_spread():
    rows = [
        FundingRow(
            exchange="Hyperliquid",
            symbol="BTC",
            rate=0.0001,
            interval_hours=1.0,
            timestamp_ms=1,
            annualized_pct=8.0,
            status="LIVE",
        ),
        FundingRow(
            exchange="Binance",
            symbol="BTC",
            rate=-0.0001,
            interval_hours=8.0,
            timestamp_ms=1,
            annualized_pct=-4.0,
            status="LIVE",
        ),
    ]
    result = detect_arbitrage(rows, min_spread_pct=5.0)
    assert result
    assert result[0]["symbol"] == "BTC"
    assert result[0]["spread_pct"] == 12.0


def test_update_funding_exchanges_add_remove():
    current = ["hyperliquid"]
    updated, message = update_funding_exchanges(current, "add", "binance")
    assert "added" in message.lower()
    assert "binance" in updated
    updated, message = update_funding_exchanges(updated, "remove", "hyperliquid")
    assert "removed" in message.lower()
    assert "hyperliquid" not in updated
