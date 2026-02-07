import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.feeds.base import FeedResult
from tui.ui.screens.profile_whale_watcher import (
    WhaleFilter,
    _extract_wallets_from_result,
    _filter_trades,
)


def test_whale_watcher_extracts_wallets_and_filters():
    result = FeedResult(
        status="ok",
        data={
            "trades": [
                {
                    "symbol": "BTC",
                    "side": "buy",
                    "size": 5,
                    "price": 10000,
                    "wallet": "0xabc",
                }
            ]
        },
        updated_ts_ms=1,
    )
    wallets = _extract_wallets_from_result(result)
    assert wallets == ["0xabc"]
    trades = result.data["trades"]
    filtered = _filter_trades(trades, side=WhaleFilter().side, min_notional=1.0)
    assert len(filtered) == 1
