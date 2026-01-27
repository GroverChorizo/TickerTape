"""View screens for Liquidation Hunter."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from tui.ui.screens.base import BaseScreen
from tui.render.sparkline import sparkline, heat_bar
from tui.models.liquidations import LiquidationSnapshot


class LiquidationTimeSeriesView(BaseScreen):
    def __init__(self) -> None:
        super().__init__(screen_id="view_liq_time", title="Liquidations Time Series", context="views")

    def on_mount(self) -> None:
        self.set_header("Liquidations | Time Series")
        self.set_status("Type 'home' to return or 'view heatmap'/'view table'.")
        self._render()

    def _render(self) -> None:
        snapshot = _get_snapshot(self.app)
        body = self.body
        if not snapshot:
            body.update("No data yet.")
            return
        series = snapshot.series_notional
        spark = sparkline(series, width=24)
        lines = ["Notional (last 15m, 1m buckets)", spark]
        body.update("\n".join(lines))


class LiquidationHeatmapView(BaseScreen):
    def __init__(self) -> None:
        super().__init__(screen_id="view_liq_heat", title="Liquidations Heatmap", context="views")

    def on_mount(self) -> None:
        self.set_header("Liquidations | Heatmap")
        self.set_status("Type 'home' to return or 'view time'/'view table'.")
        self._render()

    def _render(self) -> None:
        snapshot = _get_snapshot(self.app)
        body = self.body
        if not snapshot:
            body.update("No data yet.")
            return
        top = snapshot.top_symbols.get("15m") or snapshot.top_symbols.get("24h") or []
        max_val = max([row.get("notional", 0.0) for row in top], default=1.0)
        lines: List[str] = ["Top symbols by notional"]
        for row in top[:10]:
            symbol = row.get("symbol") or "?"
            bar = heat_bar(float(row.get("notional") or 0.0), max_val, width=16)
            lines.append(f"{symbol:<6} {bar}")
        body.update("\n".join(lines))


class LiquidationTableView(BaseScreen):
    def __init__(self) -> None:
        super().__init__(screen_id="view_liq_table", title="Liquidations Table", context="views")

    def on_mount(self) -> None:
        self.set_header("Liquidations | Table")
        self.set_status("Type 'home' to return or 'view time'/'view heatmap'.")
        self._render()

    def _render(self) -> None:
        snapshot = _get_snapshot(self.app)
        body = self.body
        if not snapshot:
            body.update("No data yet.")
            return
        lines = ["Time | Symbol | Side | Notional"]
        for event in snapshot.events[:20]:
            ts = datetime.fromtimestamp(event.ts_ms / 1000, tz=timezone.utc).strftime("%H:%M:%S")
            notional = event.notional_usd or 0.0
            lines.append(f"{ts} | {event.symbol:<6} | {event.side:<9} | ${notional:,.0f}")
        body.update("\n".join(lines))


def _get_snapshot(app) -> LiquidationSnapshot | None:
    store = getattr(app, "state_store", None)
    if store is None:
        return None
    snap = store.profile("liquidation_hunter").get_snapshot("snapshot")
    return snap.data if isinstance(snap.data, LiquidationSnapshot) else None
