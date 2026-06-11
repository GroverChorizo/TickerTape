"""Fallback-path tests: panels render gracefully with error/empty feed results.

Each test verifies that calling update_feed() with a non-OK FeedResult does not
crash and that the panel renders visible fallback content (not blank).
"""
from __future__ import annotations

import asyncio

import pytest

textual = pytest.importorskip("textual")

from textual.app import App, ComposeResult

from tui.feeds.base import FeedResult, FeedStatus
from tui.widgets.market_overview_panel import MarketOverviewPanel
from tui.widgets.liquidations_feed_panel import LiquidationsFeedPanel
from tui.widgets.whale_panel import WhalePanel
from tui.widgets.funding_panel import FundingPanel


# ── minimal host apps ──────────────────────────────────────────────────────────


class _SinglePanelApp(App):
    def __init__(self, panel) -> None:
        super().__init__()
        self._panel = panel

    def compose(self) -> ComposeResult:
        yield self._panel


# ── helpers ────────────────────────────────────────────────────────────────────


def _renderable_text(panel) -> str:
    """Return the string representation of the panel's current renderable."""
    renderable = getattr(panel, "renderable", None)
    if renderable is None:
        return ""
    return str(renderable)


# ── Day Trader: MarketOverviewPanel ────────────────────────────────────────────


def test_market_overview_panel_renders_on_error_result():
    panel = MarketOverviewPanel()
    app = _SinglePanelApp(panel)

    async def _run() -> None:
        async with app.run_test():
            panel.update_feed(
                FeedResult(
                    status=FeedStatus.ERROR,
                    data=None,
                    error="connection refused",
                )
            )

    asyncio.run(_run())
    text = _renderable_text(panel)
    assert text.strip(), "Panel renderable should not be blank on ERROR"


def test_market_overview_panel_renders_on_empty_result():
    panel = MarketOverviewPanel()
    app = _SinglePanelApp(panel)

    async def _run() -> None:
        async with app.run_test():
            panel.update_feed(
                FeedResult(status=FeedStatus.EMPTY, data=None)
            )

    asyncio.run(_run())
    text = _renderable_text(panel)
    assert text.strip(), "Panel renderable should not be blank on EMPTY"


# ── Liquidation Hunter: LiquidationsFeedPanel ─────────────────────────────────


def test_liquidations_feed_panel_renders_on_error_result():
    panel = LiquidationsFeedPanel()
    app = _SinglePanelApp(panel)

    async def _run() -> None:
        async with app.run_test():
            panel.update_feed(
                FeedResult(
                    status=FeedStatus.ERROR,
                    data=None,
                    error="timeout",
                )
            )

    asyncio.run(_run())
    text = _renderable_text(panel)
    assert text.strip(), "LiquidationsFeedPanel renderable should not be blank on ERROR"


def test_liquidations_feed_panel_renders_on_empty_result():
    panel = LiquidationsFeedPanel()
    app = _SinglePanelApp(panel)

    async def _run() -> None:
        async with app.run_test():
            panel.update_feed(
                FeedResult(status=FeedStatus.EMPTY, data=None)
            )

    asyncio.run(_run())
    text = _renderable_text(panel)
    assert text.strip(), "LiquidationsFeedPanel renderable should not be blank on EMPTY"


# ── Whale Watcher: WhalePanel ──────────────────────────────────────────────────


def test_whale_panel_renders_on_error_result():
    panel = WhalePanel()
    app = _SinglePanelApp(panel)

    async def _run() -> None:
        async with app.run_test():
            panel.update_feed(
                FeedResult(
                    status=FeedStatus.ERROR,
                    data=None,
                    error="no route to host",
                )
            )

    asyncio.run(_run())
    text = _renderable_text(panel)
    assert text.strip(), "WhalePanel renderable should not be blank on ERROR"


def test_whale_panel_renders_on_empty_trades_list():
    panel = WhalePanel()
    app = _SinglePanelApp(panel)

    async def _run() -> None:
        async with app.run_test():
            panel.update_feed(
                FeedResult(status=FeedStatus.OK, data={"trades": []})
            )

    asyncio.run(_run())
    text = _renderable_text(panel)
    assert text.strip(), "WhalePanel renderable should not be blank with empty trades"


# ── Funding Arbitrage: FundingPanel ───────────────────────────────────────────


def test_funding_panel_renders_on_error_result():
    panel = FundingPanel()
    app = _SinglePanelApp(panel)

    async def _run() -> None:
        async with app.run_test():
            panel.update_feed(
                FeedResult(
                    status=FeedStatus.ERROR,
                    data=None,
                    error="api error",
                )
            )

    asyncio.run(_run())
    text = _renderable_text(panel)
    assert text.strip(), "FundingPanel renderable should not be blank on ERROR"


def test_funding_panel_renders_on_empty_rate_list():
    panel = FundingPanel()
    app = _SinglePanelApp(panel)

    async def _run() -> None:
        async with app.run_test():
            panel.update_feed(
                FeedResult(status=FeedStatus.OK, data={"rates": []})
            )

    asyncio.run(_run())
    text = _renderable_text(panel)
    assert text.strip(), "FundingPanel renderable should not be blank with empty rates"
