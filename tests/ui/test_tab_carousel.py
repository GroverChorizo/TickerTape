import os
import sys
import json
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.core import cache as cache_store
from tui.app import TickerTapeApp
from tui.config import TuiConfig
from tui.ui.tab_carousel import TabCarousel, TabEntry


def test_tab_carousel_cycle():
    tabs = [
        TabEntry(key="home", label="Home", shortcut="1"),
        TabEntry(key="profile_day_trader", label="Day Trader", shortcut="2"),
    ]
    carousel = TabCarousel(tabs)
    assert carousel.active_key() == "home"
    carousel.select_next()
    assert carousel.active_key() == "profile_day_trader"
    carousel.select_prev()
    assert carousel.active_key() == "home"


def test_open_screen_order_persists(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_store, "CACHE_PATH", tmp_path / "cache.json")
    config = TuiConfig(
        mode="offline_demo",
        data_root=tmp_path / "data",
        profile="day_trader",
        secrets_path=None,
        alerts={},
        panel_overrides={},
        config_path=tmp_path / "config.json",
    )
    app = TickerTapeApp(config)
    app._tt_screen_stack = ["home", "profile_day_trader", "view_liq_table"]
    app._screen_titles = {
        "home": "Home",
        "profile_day_trader": "Day Trader",
        "view_liq_table": "Liquidations Table",
    }
    app._sync_open_screen_order()
    payload = json.loads(Path(tmp_path / "cache.json").read_text(encoding="utf-8"))
    assert payload["open_screens_order"] == [
        "home",
        "profile_day_trader",
        "view_liq_table",
    ]
    screens = app.get_open_screens()
    assert screens[1]["label"] == "Day Trader"
