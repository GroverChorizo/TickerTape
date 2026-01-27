import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.feeds.base import FeedResult
from tui.ui.screens.profile_whale_watcher import WhaleFilter, _build_lines


def test_whale_watcher_build_lines_sections():
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
    lines, wallets = _build_lines(result, WhaleFilter())
    text = "\n".join(lines)
    assert "Whale Trade List" in text
    assert "Directional Flow" in text
    assert "Whale Heatmap" in text
    assert "Wallets" in text
    assert wallets == ["0xabc"]
