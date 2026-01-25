"""Liquidations panel: snapshot KPIs across timeframes."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

from textual.reactive import reactive

from ..backend.snapshots import get_latest_snapshot_with_path
from ..backend.registry import get_registry
from ..state.datasets import load_datasets
from .panel_base import PanelBase


DEFAULT_TIMEFRAMES = ["10m", "1h", "4h", "24h", "1W", "1M", "1Y", "5Y"]


class LiquidationsPanel(PanelBase):
    snapshots: Dict[str, dict] = reactive({}, recompose=False)

    def __init__(self) -> None:
        super().__init__(panel_id="liquidations", title="Liquidations")

    def refresh_snapshots(self) -> None:
        registry = get_registry()
        datasets = load_datasets(registry)
        available = datasets.get("feed=liquidations_snapshots")
        timeframes = available.timeframes if available and available.timeframes else []
        combined = list(dict.fromkeys(timeframes + DEFAULT_TIMEFRAMES))
        for tf in combined:
            snap, path = get_latest_snapshot_with_path(registry, "feed=liquidations_snapshots", tf)
            if snap:
                snap["_partition_path"] = path
                self.snapshots[tf] = snap
        self.update_text(self._render_snapshots(combined))

    def _render_snapshots(self, timeframes: List[str]) -> str:
        lines: List[str] = []
        for tf in timeframes:
            snap = self.snapshots.get(tf)
            if not snap:
                lines.append(f"[{tf}] No snapshot data available. Run /ingest or complete setup wizard.")
                continue
            total = snap.get("total_notional", 0.0)
            count = snap.get("count", 0)
            cascade = "YES" if snap.get("cascade_detected") else "no"
            velocity = snap.get("velocity_score", 0.0)
            computed = snap.get("computed_at_ts_ms")
            computed_str = self._fmt_ts(computed)
            age = self._age_seconds(computed)
            run_id = snap.get("run_id", "unknown")
            partition_path = snap.get("_partition_path") or "unknown"
            lines.append(
                f"[{tf}] count={count} total=${total:,.0f} cascade={cascade} velocity={velocity:.2f} "
                f"computed={computed_str} age={age} run_id={run_id}"
            )
            lines.append(f"    Partition: {partition_path}")
            top_symbols = snap.get("top_symbols", [])
            if top_symbols:
                top_fmt = ", ".join(
                    f"{item.get('symbol', '?')} ${item.get('notional', 0):,.0f}" for item in top_symbols[:3]
                )
                lines.append(f"    Top symbols: {top_fmt}")
            top_exchanges = snap.get("top_exchanges", [])
            if top_exchanges:
                exch_fmt = ", ".join(
                    f"{item.get('exchange', '?')} ${item.get('notional', 0):,.0f}" for item in top_exchanges[:3]
                )
                lines.append(f"    Top exchanges: {exch_fmt}")
        return "\n".join(lines) if lines else "No liquidation snapshots available."

    @staticmethod
    def _fmt_ts(ts_ms: int | None) -> str:
        if not ts_ms:
            return "unknown"
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

    @staticmethod
    def _age_seconds(ts_ms: int | None) -> str:
        if not ts_ms:
            return "unknown"
        now = datetime.now(timezone.utc)
        then = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        seconds = int((now - then).total_seconds())
        return f"{seconds}s"
