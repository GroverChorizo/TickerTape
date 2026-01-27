import asyncio
import pytest

textual = pytest.importorskip("textual")

from textual.app import App, ComposeResult

from backend.storage import DatasetRegistry
from tui.feeds.base import FeedResult
from tui.feeds.liquidations import (
    LiquidationsRadarFeed,
    _normalize_event,
    _normalize_timeframe_stats,
)
from tui.widgets.liquidations_radar import LiquidationsRadarPanel
from tui.ui.screens.profile_liquidation import (
    _build_liquidation_lines,
    _render_liquidation_distance,
)
from tui.models.liquidations import LiquidationSnapshot
from tui.state.profiles import get_profile


class _PanelApp(App):
    def __init__(self, panel) -> None:
        super().__init__()
        self._panel = panel

    def compose(self) -> ComposeResult:
        yield self._panel


def test_liquidation_event_normalization_minimal():
    raw = {
        "time": 1700000000,
        "coin": "BTC",
        "side": "short",
        "value_usd": 50000,
        "price": 50000,
        "sz": 1,
        "address": "0xabc",
    }
    event = _normalize_event(raw, "moondev")
    assert event is not None
    assert event.ts_ms == 1700000000 * 1000
    assert event.symbol == "BTC"
    assert event.side == "short_liq"
    assert event.notional_usd == 50000
    assert event.liquidated_wallet == "0xabc"


def test_liquidation_timeframe_stats_minimal():
    raw = {
        "stats": {
            "total_count": 10,
            "total_value_usd": 100000,
            "long_count": 4,
            "short_count": 6,
            "long_value_usd": 40000,
            "short_value_usd": 60000,
        }
    }
    stats = _normalize_timeframe_stats(raw)
    assert stats["total_count"] == 10
    assert stats["total_notional"] == 100000
    assert stats["long_count"] == 4
    assert stats["short_count"] == 6


def test_liquidation_panel_error_includes_http_status():
    panel = LiquidationsRadarPanel()
    error_line = (
        "GET https://api.moondev.com/api/liquidations/1h.json -> HTTP 404: Not Found"
    )
    result = FeedResult(status="error", error=error_line)

    app = _PanelApp(panel)

    async def _run() -> None:
        async with app.run_test():
            panel.update_feed(result)

    asyncio.run(_run())
    content = panel.content
    text = content.plain if hasattr(content, "plain") else str(content)
    assert error_line in text


def test_liquidation_hunter_profile_panels():
    profile = get_profile("liquidation_hunter")
    for panel_id in [
        "liquidations_radar",
        "liquidations_top",
        "liquidations_context",
        "capture_status",
    ]:
        assert panel_id in profile.default_panel_order


def test_liquidations_feed_failure_does_not_raise(tmp_path):
    class DummyClient:
        def get_json(self, *_args, **_kwargs):
            raise RuntimeError("boom")

    registry = DatasetRegistry(path=tmp_path / "_registry.json")
    feed = LiquidationsRadarFeed(DummyClient(), registry=registry)
    result = feed.fetch_result()
    assert result.status in {"error", "disconnected"}


def test_liquidation_distance_section():
    positions = [
        {
            "symbol": "BTC",
            "liquidation_price": 9000,
            "mark_price": 10000,
            "side": "long",
        }
    ]
    lines = _render_liquidation_distance(positions)
    assert lines[0] == "Liquidation Distance"
    assert any("BTC" in line for line in lines[1:])


def test_liquidation_hunter_build_lines_sections():
    payload = {
        "events": [
            {
                "ts_ms": 1,
                "symbol": "BTC",
                "side": "long_liq",
                "notional_usd": 1000,
                "price": 100,
                "size": 10,
                "source": "moondev",
                "liquidated_wallet": None,
            }
        ],
        "rollups": {
            "1m": {"count": 1, "notional": 1000, "long_count": 1, "short_count": 0}
        },
        "series": {"notional": [1000.0], "count": [1.0]},
        "cascade": {"level": "LOW", "score": 0.0, "reason": "ok"},
        "top_symbols": {"15m": [{"symbol": "BTC", "notional": 1000}]},
        "errors": [],
        "capture": {
            "enabled": False,
            "dataset": "",
            "timeframe": "",
            "file_count": 0,
            "total_bytes": 0,
        },
    }
    snapshot = LiquidationSnapshot.from_payload(payload)
    lines = _build_liquidation_lines(snapshot, None, "BTC", None)
    text = "\n".join(lines)
    assert "Liquidation Heatmap" in text
    assert "Liquidation Distance" in text
