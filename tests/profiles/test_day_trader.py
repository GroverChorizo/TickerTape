import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.feeds.base import FeedResult
from tui.ui.screens.profile_day_trader import DayTraderState, _build_lines


def test_day_trader_build_lines_includes_sections():
    state = DayTraderState(watchlist=["BTC", "ETH"])
    state.price_history = {"BTC": [1.0, 2.0], "ETH": [3.0, 2.5]}
    market = FeedResult(
        status="ok",
        data={
            "top_coins": [
                {"symbol": "BTC", "open_interest": 10, "funding": 0.001},
                {"symbol": "ETH", "open_interest": 5, "funding": -0.002},
            ]
        },
        updated_ts_ms=1,
    )
    whale = FeedResult(status="ok", data={"trades": []}, updated_ts_ms=1)
    liq = FeedResult(status="ok", data={"snapshot": {"stats": {}}}, updated_ts_ms=1)

    lines = _build_lines(state, market, whale, liq)
    text = "\n".join(lines)
    assert "Price Chart" in text
    assert "Top Positions" in text
    assert "Whale Flow" in text
    assert "Liquidation Stats" in text
