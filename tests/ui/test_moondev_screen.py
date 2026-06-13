"""Smoke tests for the MoonDev Data console screen.

Never hits the network: clients are injected (configured/unconfigured) and the
offline guard is exercised. Mirrors the host-app pattern in
test_profile_tab_switch_smoke.py.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

pytest.importorskip("textual")

from textual.app import App

from providers.datalayer import DataLayerClient
from tui.config import TuiConfig
from tui.state.session import SessionState
from tui.ui.screens.moondev import MoonDevScreen, render_result


class _Host(App):
    def __init__(self, screen, mode="offline_demo"):
        super().__init__()
        self._screen = screen
        self.session_state = SessionState(active_profile="day_trader", profiles={})
        self.selected_symbol = "BTC"
        self.config = TuiConfig(
            mode=mode,
            data_root=Path("data/parquet"),
            profile="day_trader",
            config_path=Path("data/test_config.json"),
            secrets_path=None,
        )

    def on_mount(self):
        self.push_screen(self._screen)

    def get_open_screens(self):
        return [{"key": self._screen.id or "screen", "label": "MoonDev Data"}]

    def is_alert_enabled(self, _name):
        return False

    def emit_alert(self, **_kw):
        return None

    def set_wallets(self, _w):
        return None


def _run(screen, after, mode="offline_demo"):
    app = _Host(screen, mode=mode)

    async def _main():
        async with app.run_test() as pilot:
            await pilot.pause()
            after(app)
            await pilot.pause()

    asyncio.run(_main())


def _meta_text(app) -> str:
    return str(app.screen._meta.renderable)


def test_screen_mounts_and_shows_disclaimer():
    seen = {}

    def after(app):
        seen["disc"] = str(app.screen.query_one("#moondev_disclaimer").renderable)

    _run(MoonDevScreen(client=DataLayerClient(api_key=None)), after)
    assert "not financial advice" in seen["disc"].lower()


def test_offline_blocks_live_call():
    seen = {}

    def after(app):
        app.screen._run("hip3 meta")  # configured key, but app is offline
        seen["meta"] = _meta_text(app)

    _run(MoonDevScreen(client=DataLayerClient(api_key="k")), after, mode="offline_demo")
    assert "offline" in seen["meta"].lower()


def test_unconfigured_blocks_live_call():
    seen = {}

    def after(app):
        app.screen._run("hip3 meta")  # online, but no key
        seen["meta"] = _meta_text(app)

    _run(MoonDevScreen(client=DataLayerClient(api_key=None)), after, mode="online")
    assert "not configured" in seen["meta"].lower()


def test_invalid_command_reports_error_without_network():
    seen = {}

    def after(app):
        app.screen._run("hip3 bogus")  # rejected before any fetch
        seen["meta"] = _meta_text(app)

    _run(MoonDevScreen(client=DataLayerClient(api_key="k")), after, mode="online")
    assert "error" in seen["meta"].lower()


def test_help_and_clear_commands():
    seen = {}

    def after(app):
        app.screen._run("help")
        seen["help"] = str(app.screen._results.renderable)
        app.screen._run("clear")
        seen["cleared"] = str(app.screen._results.renderable)

    _run(MoonDevScreen(client=DataLayerClient(api_key="k")), after, mode="online")
    assert "hip3" in seen["help"].lower()
    assert seen["cleared"].strip() == ""


def test_render_result_variants():
    assert render_result([{"a": 1, "b": 2}, {"a": 3}]) is not None
    assert render_result({"longs": [{"x": 1}], "n": 2}) is not None
    assert render_result({"a": 1}) is not None
    assert render_result("plain text") is not None
