import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.feeds.base import FeedResult
from tui.ui.screens.profile_funding_arbitrage import _extract_arbitrage


def test_funding_arbitrage_extracts_arbitrage():
    payload = {
        "rows": [
            {
                "exchange": "Hyperliquid",
                "symbol": "BTC",
                "annualized_pct": 5.0,
                "status": "LIVE",
            }
        ],
        "arbitrage": [
            {
                "symbol": "BTC",
                "spread_pct": 6.0,
                "max_exchange": "Hyperliquid",
                "min_exchange": "Binance",
            }
        ],
    }
    result = FeedResult(status="ok", data=payload, updated_ts_ms=1)
    arb = _extract_arbitrage(result)
    assert "arbitrage" in arb
    assert isinstance(arb["arbitrage"], list)
