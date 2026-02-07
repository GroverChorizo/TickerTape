import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.ui.screens.profile_day_trader import DayTraderScreen


def test_day_trader_panels_exist():
    screen = DayTraderScreen()
    assert screen.market_panel.id == "market_overview"
    assert screen.orderbook_panel.id == "orderbook"
    assert screen.whale_panel.id == "whale_trades"
    assert screen.liquidations_panel.id == "liquidations_feed"
    assert screen.funding_panel.id == "funding_rates"
    assert screen.positions_panel.id == "positions"
