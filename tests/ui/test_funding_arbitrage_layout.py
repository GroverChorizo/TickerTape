import os
import sys

from textual.containers import Horizontal, Vertical

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.ui.screens.profile_funding_arbitrage import FundingArbitrageScreen


def test_funding_arbitrage_layout_structure():
    screen = FundingArbitrageScreen()
    assert isinstance(screen._body, Vertical)
    assert screen._body.id == "screen_body"
    assert isinstance(screen._core_row_top, Horizontal)
    assert "panel-row" in screen._core_row_top.classes
    assert "panel-row" in screen._core_row_bottom.classes
    assert "panel-row" in screen._hlp_row.classes

    assert screen.funding_panel.id == "funding"
    assert screen.orderbook_panel.id == "orderbook"
    assert screen.arb_panel.id == "funding_arb"
    assert screen.hlp_panel.id == "hlp_summary"
    assert screen.orderflow_panel.id == "orderflow_stats"
