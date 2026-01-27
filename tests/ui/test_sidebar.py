import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.ui.sidebar import Sidebar, SidebarEntry
from tui.ui.tabbar import TabBar, TabItem


def test_sidebar_compact_mode_renders_short_labels():
    entries = [
        SidebarEntry(key="home", label="Home", short="H"),
        SidebarEntry(key="day_trader", label="Day Trader", short="D"),
    ]
    sidebar = Sidebar(entries)
    sidebar.set_active("home")
    full = str(sidebar.renderable)
    assert "Home" in full

    sidebar.set_compact(True)
    compact = str(sidebar.renderable)
    assert "Home" not in compact
    assert "H" in compact


def test_tabbar_switches_tabs():
    tabs = [
        TabItem(key="home", label="Home", short="H"),
        TabItem(key="day_trader", label="Day Trader", short="D"),
        TabItem(key="liquidation_hunter", label="Liquidation Hunter", short="L"),
    ]
    tabbar = TabBar(tabs)
    assert tabbar.active_key() == "home"
    tabbar.select_next()
    assert tabbar.active_key() == "day_trader"
    tabbar.select_prev()
    assert tabbar.active_key() == "home"
