import os
import sys

from textual.containers import Horizontal, Vertical

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.ui.screens.profile_liquidation import LiquidationHunterScreen


def test_liquidation_layout_structure():
    screen = LiquidationHunterScreen()
    assert isinstance(screen._body, Vertical)
    assert screen._body.id == "screen_body"
    assert isinstance(screen._core_row_top, Horizontal)
    assert "panel-row" in screen._core_row_top.classes
    assert "panel-row" in screen._core_row_bottom.classes
    assert "panel-row" in screen._adv_row_top.classes
    assert "panel-row" in screen._adv_row_bottom.classes

    assert screen.liquidations_panel.id == "liquidations_feed"
    assert screen.orderbook_panel.id == "orderbook"
    assert screen.funding_panel.id == "funding_rates"
    assert screen.positions_panel.id == "positions"
    assert screen.whale_panel.id == "whale_trades"
    assert screen.stats_panel.id == "liq_stats"
    assert screen.hip3_panel.id == "liq_hip3"
    assert screen.combined_panel.id == "liq_combined"
