import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.app import TickerTapeApp
from tui.config import TuiConfig


def test_watchlist_command_updates_cache(tmp_path):
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
    message = app._cmd_watchlist("watchlist", ["BTC,ETH"])
    assert "Watchlist set" in message
    assert app.get_watchlist() == ["BTC", "ETH"]
