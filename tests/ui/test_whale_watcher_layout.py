import os
import sys

from textual.containers import Horizontal, Vertical

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.ui.screens.profile_whale_watcher import WhaleWatcherScreen


def test_whale_watcher_layout_structure():
    screen = WhaleWatcherScreen()
    assert isinstance(screen._body, Vertical)
    assert screen._body.id == "screen_body"
    assert isinstance(screen._core_row_top, Horizontal)
    assert "panel-row" in screen._core_row_top.classes
    assert "panel-row" in screen._core_row_bottom.classes
    assert "panel-row" in screen._signals_row_top.classes

    assert screen.whale_panel.id == "whales"
    assert screen.wallet_panel.id == "wallets"
    assert screen.wallet_detail_panel.id == "wallet_detail"
    assert screen.insights_panel.id == "whale_insights"
    assert screen.smart_money_panel.id == "smart_money"
    assert screen.whale_addresses_panel.id == "whale_insights_alt"
