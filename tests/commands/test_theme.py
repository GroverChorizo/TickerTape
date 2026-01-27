import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.app import TickerTapeApp
from tui.config import TuiConfig


def test_theme_command_updates_theme(tmp_path):
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
    message = app._cmd_theme("theme", ["matrix"])
    assert "Theme set" in message
    assert app.theme_manager.current_id() == "matrix"
    tokens = app.theme_tokens
    assert tokens.get("background_primary") == app.theme_manager.current().bg.primary
