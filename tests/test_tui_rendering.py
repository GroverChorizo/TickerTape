import os
import sys

import asyncio
import pytest

textual = pytest.importorskip("textual")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from textual.app import App, ComposeResult

from tui.widgets.liquidations_panel import LiquidationsPanel
from tui.state.datasets import DatasetInfo


class _TestApp(App):
    def __init__(self, panel: LiquidationsPanel) -> None:
        super().__init__()
        self._panel = panel

    def compose(self) -> ComposeResult:
        yield self._panel


def test_liquidations_panel_handles_markup_strings(monkeypatch):
    panel = LiquidationsPanel()
    app = _TestApp(panel)
    dangerous = "[10m\\date=2026-01-25\\part-123.parquet]"

    def fake_load_datasets(_registry):
        return {"feed=liquidations_snapshots": DatasetInfo(name="feed=liquidations_snapshots", timeframes=[dangerous])}

    def fake_get_registry():
        class DummyRegistry:
            def list_datasets(self):
                return {}

        return DummyRegistry()

    def fake_get_latest_snapshot_with_path(_registry, _dataset, _timeframe):
        return None, None

    monkeypatch.setattr("tui.widgets.liquidations_panel.load_datasets", fake_load_datasets)
    monkeypatch.setattr("tui.widgets.liquidations_panel.get_registry", fake_get_registry)
    monkeypatch.setattr(
        "tui.widgets.liquidations_panel.get_latest_snapshot_with_path",
        fake_get_latest_snapshot_with_path,
    )

    async def _run() -> None:
        async with app.run_test():
            panel.refresh_snapshots()

    asyncio.run(_run())


def test_liquidations_panel_handles_empty_registry(monkeypatch):
    panel = LiquidationsPanel()
    app = _TestApp(panel)

    def fake_load_datasets(_registry):
        return {}

    def fake_get_registry():
        class DummyRegistry:
            def list_datasets(self):
                return {}

        return DummyRegistry()

    monkeypatch.setattr("tui.widgets.liquidations_panel.load_datasets", fake_load_datasets)
    monkeypatch.setattr("tui.widgets.liquidations_panel.get_registry", fake_get_registry)

    monkeypatch.setattr(
        "tui.widgets.liquidations_panel.get_latest_snapshot_with_path",
        lambda *_: (None, None),
    )

    async def _run() -> None:
        async with app.run_test():
            panel.refresh_snapshots()

    asyncio.run(_run())
