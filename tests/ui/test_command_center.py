"""Smoke tests for the Command Center screen.

Never hits the network: the host app is offline_demo (so on_mount renders the
placeholder), and the data path is exercised by calling `_render` directly with
sample keyless data. Mirrors the host-app pattern in test_moondev_screen.py.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

pytest.importorskip("textual")

from rich.console import Console
from textual.app import App

from tui.config import TuiConfig
from tui.state.session import SessionState
from tui.ui.screens.command_center import CommandCenterScreen, _closes_from_candles


class _Host(App):
    def __init__(self, screen):
        super().__init__()
        self._screen = screen
        self.session_state = SessionState(active_profile="day_trader", profiles={})
        self.selected_symbol = "BTC"
        self.config = TuiConfig(
            mode="offline_demo",
            data_root=Path("data/parquet"),
            profile="day_trader",
            config_path=Path("data/test_config.json"),
            secrets_path=None,
        )

    def on_mount(self):
        self.push_screen(self._screen)

    def get_open_screens(self):
        return [{"key": "command_center", "label": "Command Center"}]

    def is_alert_enabled(self, _name):
        return False

    def emit_alert(self, **_kw):
        return None

    def set_wallets(self, _w):
        return None


def _run(screen, after):
    app = _Host(screen)

    async def _main():
        async with app.run_test() as pilot:
            await pilot.pause()
            after(app)
            await pilot.pause()

    asyncio.run(_main())


def _text(renderable) -> str:
    console = Console(record=True, width=120)
    console.print(renderable)
    return console.export_text()


def test_closes_from_candles_parses_hl_shape():
    raw = [{"t": 1, "c": "100.5"}, {"t": 2, "c": "101.0"}, {"t": 3, "c": 99}]
    assert _closes_from_candles(raw) == [100.5, 101.0, 99.0]


def test_offline_shows_placeholder():
    seen = {}

    def after(app):
        seen["regime"] = str(app.screen._regime.renderable)

    _run(CommandCenterScreen(), after)
    assert "offline" in seen["regime"].lower()


def test_render_populates_panels_with_analytics():
    snapshot = [
        {"symbol": "BTC", "funding": 0.0001, "open_interest": 1000.0},
        {"symbol": "ETH", "funding": -0.0002, "open_interest": 2000.0},
    ]
    closes = {
        "BTC": [100, 101, 102, 103, 104, 105],
        "ETH": [10, 10.1, 10.2, 10.3, 10.4, 10.5],
    }
    seen = {}

    def after(app):
        app.screen._render(snapshot, closes, "BTC", {})
        seen["regime"] = _text(app.screen._regime.renderable)
        seen["corr"] = _text(app.screen._corr.renderable)
        seen["flow"] = _text(app.screen._flow.renderable)

    _run(CommandCenterScreen(), after)
    assert "Trend" in seen["regime"]
    assert "BTC" in seen["corr"] and "ETH" in seen["corr"]
    assert "Funding" in seen["flow"]
