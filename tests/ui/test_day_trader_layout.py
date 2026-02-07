import os
import sys

from textual.containers import Horizontal, Vertical

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.ui.screens.profile_day_trader import DayTraderScreen


def test_day_trader_layout_structure():
    screen = DayTraderScreen()
    assert isinstance(screen._body, Vertical)
    assert screen._body.id == "screen_body"
    assert isinstance(screen._row_top, Horizontal)
    assert screen._row_mid.id == "dt_row_mid"
    assert screen._row_bottom.id == "dt_row_bottom"
