from __future__ import annotations

from typing import Any, Dict, List, Optional

from rich.table import Table
from rich.panel import Panel
from rich.console import RenderableType
from textual.widget import Widget


class WhalePositionsWidget(Widget):
    """Show top whale positions / PnL-like summary.

    - Public API: `update_from_whales(payload)` expects a dict or list of trades
    """

    def __init__(self, *, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self._last: Optional[List[Dict[str, Any]]] = None

    def update_from_whales(self, payload: Optional[Any]) -> None:
        try:
            if isinstance(payload, dict) and "trades" in payload:
                rows = payload.get("trades")
            elif isinstance(payload, list):
                rows = payload
            else:
                rows = []
            self._last = [r for r in (rows or []) if isinstance(r, dict)][:8]
        except Exception:
            self._last = []
        try:
            self.refresh()
        except Exception:
            pass

    def render(self) -> RenderableType:
        table = Table(expand=True)
        table.add_column("Coin", width=6)
        table.add_column("Side", width=6)
        table.add_column("Notional", justify="right")
        if not self._last:
            table.add_row("n/a", "n/a", "n/a")
            return Panel(table, title="Whale Positions")
        for t in self._last:
            coin = t.get("symbol") or t.get("coin") or t.get("asset") or "?"
            side = t.get("side") or t.get("direction") or "?"
            notional = t.get("notional") or t.get("size") or 0
            try:
                nstr = f"${float(notional):,.0f}"
            except Exception:
                nstr = str(notional)
            table.add_row(str(coin), str(side), nstr)
        return Panel(table, title="Whale Positions")