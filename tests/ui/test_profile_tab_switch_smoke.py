import asyncio
from pathlib import Path

import pytest

textual = pytest.importorskip("textual")

from textual.app import App
from textual.widgets import TabbedContent

from tui.config import TuiConfig
from tui.feeds.base import FeedResult
from tui.state.session import SessionState
from tui.ui.screens.profile_day_trader import DayTraderScreen
from tui.ui.screens.profile_liquidation import LiquidationHunterScreen
from tui.ui.screens.profile_whale_watcher import WhaleWatcherScreen
from tui.ui.screens.profile_funding_arbitrage import FundingArbitrageScreen


class _ScreenHostApp(App):
    def __init__(self, screen) -> None:
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

    def on_mount(self) -> None:
        self.push_screen(self._screen)

    def get_open_screens(self):
        return [{"key": self._screen.id or "screen", "label": "Screen"}]

    def is_alert_enabled(self, _alert_name: str) -> bool:
        return False

    def emit_alert(self, **_kwargs) -> None:
        return None

    def set_wallets(self, _wallets) -> None:
        return None


def _run_tab_switch(screen, tab_ids: list[str], update_fn=None) -> None:
    app = _ScreenHostApp(screen)

    async def _run() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            tabs = app.screen.query_one(TabbedContent)
            for tab_id in tab_ids:
                tabs.active = tab_id
                if update_fn is not None:
                    update_fn(app.screen, tab_id)
                await pilot.pause()

    asyncio.run(_run())


def test_day_trader_tabs_switch_without_exceptions():
    def _update(screen, tab_id: str) -> None:
        if tab_id == "dt_tab_signals":
            screen.hlp_panel.update_feed(
                FeedResult(
                    status="ok",
                    data={"health": "ok"},
                    updated_ts_ms=1_700_000_000_000,
                )
            )

    _run_tab_switch(DayTraderScreen(), ["dt_tab_core", "dt_tab_signals"], _update)


def test_liquidation_hunter_tabs_switch_without_exceptions():
    _run_tab_switch(
        LiquidationHunterScreen(),
        ["liq_tab_core", "liq_tab_advanced"],
    )


def test_whale_watcher_tabs_switch_without_exceptions():
    _run_tab_switch(
        WhaleWatcherScreen(),
        ["whale_tab_core", "whale_tab_signals"],
    )


def test_funding_arbitrage_tabs_switch_without_exceptions():
    _run_tab_switch(
        FundingArbitrageScreen(),
        ["funding_tab_core", "funding_tab_hlp"],
    )
