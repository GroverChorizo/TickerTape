from __future__ import annotations

from typing import Any, Dict, Optional

from rich.console import RenderableType
from rich.table import Table
from rich.panel import Panel
from rich.style import Style

from textual.widget import Widget


class OrderbookImbalanceWidget(Widget):
    """Render a compact orderbook imbalance view (bids vs asks) for a symbol.

    - Exposes `update_from_orderbook(payload)` which accepts the parsed
      orderbook dict (keys: 'bids' and 'asks' -> list of [px, qty]).
    - Keeps the most-recent imbalance snapshot and renders a mini bar chart
      + summary stats (spread, best bid/ask).
    """

    DEFAULT_CSS = """
OrderbookImbalanceWidget {
    height: auto;
}
"""

    def __init__(self, *, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self._last: Optional[Dict[str, Any]] = None

    # Public API used by screens / tests
    def update_from_orderbook(self, payload: Optional[Dict[str, Any]]) -> None:
        self._last = payload
        # trigger a repaint in Textual
        try:
            self.refresh()
        except Exception:
            pass

    # Rendering logic
    def render(self) -> RenderableType:
        payload = self._last or {}
        bids = payload.get("bids") or []
        asks = payload.get("asks") or []
        best_bid = _first_price(bids)
        best_ask = _first_price(asks)
        spread = None
        if best_bid is not None and best_ask is not None:
            try:
                spread = best_ask - best_bid
            except Exception:
                spread = None

        # compute simple imbalance by summing top-N sizes
        depth = min(5, max(len(bids), len(asks)))
        bid_vol = _sum_size(bids[:depth])
        ask_vol = _sum_size(asks[:depth])
        total = max(1.0, bid_vol + ask_vol)
        bid_pct = (bid_vol / total) * 100.0
        ask_pct = (ask_vol / total) * 100.0

        table = Table.grid(expand=True)
        table.add_column("left", ratio=3)
        table.add_column("right", ratio=1)

        title = payload.get("symbol") or payload.get("coin") or "MARKET"
        header = f"Orderbook Imbalance — {title}"

        # bar visualization using Unicode blocks
        bar_width = 24
        bid_bar = int((bid_pct / 100.0) * bar_width)
        ask_bar = int((ask_pct / 100.0) * bar_width)
        bid_str = "█" * bid_bar + "░" * (bar_width - bid_bar)
        ask_str = "█" * ask_bar + "░" * (bar_width - ask_bar)

        left_lines = []
        left_lines.append(f"Bids {bid_vol:.2f} ({bid_pct:.0f}%)")
        left_lines.append(bid_str)
        left_lines.append("")
        left_lines.append(f"Asks {ask_vol:.2f} ({ask_pct:.0f}%)")
        left_lines.append(ask_str)

        right_lines = []
        right_lines.append(f"best bid\n{best_bid if best_bid is not None else 'n/a'}")
        right_lines.append("")
        right_lines.append(f"best ask\n{best_ask if best_ask is not None else 'n/a'}")
        if spread is not None:
            right_lines.append("")
            right_lines.append(f"spread\n{spread:.2f}")

        table.add_row("\n".join(left_lines), "\n".join(right_lines))

        # color the panel depending on imbalance
        style = Style(color="green") if bid_vol >= ask_vol else Style(color="red")
        return Panel(table, title=header, border_style=style)


def _level_price_size(entry: Any) -> tuple[Optional[float], Optional[float]]:
    if isinstance(entry, dict):
        price = entry.get("price") or entry.get("px")
        size = entry.get("size") or entry.get("qty") or entry.get("sz")
    elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
        price, size = entry[0], entry[1]
    else:
        return None, None
    try:
        p = float(price) if price is not None else None
    except (TypeError, ValueError):
        p = None
    try:
        s = float(size) if size is not None else None
    except (TypeError, ValueError):
        s = None
    return p, s


def _first_price(levels: list) -> Optional[float]:
    for entry in levels:
        price, _ = _level_price_size(entry)
        if price is not None:
            return price
    return None


def _sum_size(levels: list) -> float:
    total = 0.0
    for entry in levels:
        _, size = _level_price_size(entry)
        if size is not None:
            total += size
    return total
