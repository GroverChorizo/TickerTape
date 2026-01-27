import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tui.app import TickerTapeApp
from tui.config import TuiConfig
from tui.ui.widgets.command_palette import CommandPalette


def test_palette_suggestions_include_commands(tmp_path):
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
    app._command_history = ["help", "profile day_trader"]
    suggestions = app.palette_suggestions("pro")
    assert any("profile" in s for s in suggestions)


def test_command_palette_selects_items():
    palette = CommandPalette()
    palette.set_items(["help - Show commands", "home - Return home"])
    assert "help" in palette.current_item()
    palette.select_next()
    assert "home" in palette.current_item()
