"""Funding rates panel with explicit missing-data messaging."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

from ..backend.registry import get_registry
from ..backend.snapshots import get_latest_snapshot
from ..state.datasets import load_datasets
from .panel_base import PanelBase


class FundingPanel(PanelBase):
    def __init__(self) -> None:
        super().__init__(panel_id="funding", title="Funding")

    def refresh_panel(self) -> None:
        registry = get_registry()
        datasets = load_datasets(registry)
        if "feed=funding_rates" not in datasets:
            self.update("Funding feed unavailable (stub or missing).")
            return
        snap = get_latest_snapshot(registry, "feed=funding_rates", "1h")
        if not snap:
            self.update("No funding snapshot data available.")
            return
        lines: List[str] = []
        lines.append(f"Symbol: {snap.get('symbol', 'n/a')}")
        lines.append(f"Rate: {snap.get('rate', 'n/a')}")
        lines.append(f"Period: {snap.get('period', 'n/a')}")
        lines.append(f"Computed: {self._fmt_ts(snap.get('timestamp_ms'))}")
        self.update("\n".join(lines))

    @staticmethod
    def _fmt_ts(ts_ms: int | None) -> str:
        if not ts_ms:
            return "unknown"
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
