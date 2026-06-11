import asyncio
import pytest

textual = pytest.importorskip("textual")

from textual.app import App, ComposeResult
from textual.widgets import TabbedContent
from rich.console import Group

from tui.feeds.base import FeedResult
from tui.state.session import SessionState
from tui.widgets.raw_json_panel import RawJsonPanel
from tui.ui.screens.profile_day_trader import DayTraderScreen


class _PanelApp(App):
    def __init__(self, panel: RawJsonPanel) -> None:
        super().__init__()
        self._panel = panel

    def compose(self) -> ComposeResult:
        yield self._panel


class _DayTraderHostApp(App):
    def __init__(self) -> None:
        super().__init__()
        self._screen = DayTraderScreen()
        self.session_state = SessionState(active_profile="day_trader", profiles={})

    def on_mount(self) -> None:
        self.push_screen(self._screen)

    def get_open_screens(self):
        return [{"key": "profile_day_trader", "label": "Day Trader"}]


def test_raw_json_panel_group_contains_renderables():
    panel = RawJsonPanel("raw_json_test", "Raw JSON")
    app = _PanelApp(panel)

    async def _run() -> None:
        async with app.run_test():
            panel.update_feed(
                FeedResult(
                    status="ok",
                    data={"foo": {"bar": 1}},
                    updated_ts_ms=1_700_000_000_000,
                )
            )

    asyncio.run(_run())
    renderable = panel.renderable
    assert isinstance(renderable, Group)
    assert all(not isinstance(item, tuple) for item in renderable.renderables)


def test_day_trader_signals_tab_switch_renders_raw_panels():
    app = _DayTraderHostApp()

    async def _run() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            tabs = screen.query_one(TabbedContent)
            tabs.active = "dt_tab_signals"
            # Populate one signals panel to exercise Group rendering path.
            screen.hlp_panel.update_feed(
                FeedResult(
                    status="ok",
                    data={"last_updated": "ok"},
                    updated_ts_ms=1_700_000_000_000,
                )
            )
            await pilot.pause()

    asyncio.run(_run())
