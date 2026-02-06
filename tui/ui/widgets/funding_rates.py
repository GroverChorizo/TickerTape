from __future__ import annotations

from typing import Any, Dict, Optional

from rich.table import Table
from rich.panel import Panel
from rich.console import RenderableType
from textual.widget import Widget


class FundingRatesWidget(Widget):
    """Compact funding-rates table for top symbols/exchanges.

    - Public API: `update_from_funding(payload)` accepts a dict like
      {"funding": {"BTC": {"latest": {...}}, ...}}
    """

    def __init__(self, *, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self._last: Optional[Dict[str, Any]] = None

    def update_from_funding(self, payload: Optional[Dict[str, Any]]) -> None:
        self._last = payload
        try:
            self.refresh()
        except Exception:
            pass

    def render(self) -> RenderableType:
        payload = self._last or {}
        funding = payload.get("funding") if isinstance(payload, dict) else None
        table = Table(expand=True)
        table.add_column("Asset", width=6)
        table.add_column("Rate", justify="right")
        table.add_column("Source", width=10)
        if not funding:
            table.add_row("n/a", "n/a", "n/a")
            return Panel(table, title="Funding Rates")
        rows = []
        for sym, info in sorted(funding.items(), key=lambda x: x[0])[:8]:
            latest = info.get("latest") if isinstance(info, dict) else None
            rate = latest.get("rate") if isinstance(latest, dict) else None
            try:
                rate_str = f"{float(rate):+.4f}%"
            except Exception:
                rate_str = "n/a"
            rows.append((sym, rate_str, info.get("source") or "HL"))
        for r in rows:
            table.add_row(r[0], r[1], r[2])
        return Panel(table, title="Funding Rates")