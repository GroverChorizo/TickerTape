"""Whale activity panel."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ..backend.registry import get_registry
from ..backend.queries import recent_events
from ..state.datasets import load_datasets
from .panel_base import PanelBase


class WhalePanel(PanelBase):
    def __init__(self) -> None:
        super().__init__(panel_id="whales", title="Whale Activity")

    def refresh_panel(self) -> None:
        registry = get_registry()
        datasets = load_datasets(registry)
        if "feed=whale_trades" not in datasets:
            self.update("Whale trades feed unavailable (stub or missing).")
            return
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        events = recent_events(registry, "feed=whale_trades", now_ms - 60 * 60 * 1000)
        if not events:
            self.update("No whale trade data available in the last hour.")
            return
        lines: List[str] = ["Recent whale trades (last hour):"]
        for event in events[-5:]:
            symbol = event.get("symbol", "?")
            side = event.get("side", "?")
            size = event.get("size", "?")
            price = event.get("price", "?")
            lines.append(f"- {symbol} {side} size={size} price={price}")
        self.update("\n".join(lines))
