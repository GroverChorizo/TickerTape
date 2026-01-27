"""Funding Arbitrage profile screen."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import time

from backend.network import NetworkClient
from backend.storage import DatasetRegistry
from tui.feeds.base import FeedResult
from tui.feeds.funding import MultiExchangeFundingFeed
from tui.feeds.hyperliquid import HyperliquidClient
from tui.render.sparkline import heat_bar
from tui.ui.screens.base import BaseScreen


class FundingArbitrageScreen(BaseScreen):
    def __init__(self) -> None:
        super().__init__(
            screen_id="profile_funding_arbitrage",
            title="Funding Arbitrage",
            context="funding_arbitrage",
        )
        self._feed: Optional[MultiExchangeFundingFeed] = None
        self._next_fetch = 0.0
        self._result: Optional[FeedResult] = None

    def on_mount(self) -> None:
        self.set_header("Funding Arbitrage | LIVE")
        self.set_status("Waiting for data...")
        self._build_feed()
        self.set_interval(1.0, self._tick)

    def _build_feed(self) -> None:
        registry = DatasetRegistry(path=self.app.config.data_root / "_registry.json")
        exchanges = getattr(self.app.config, "funding_exchanges", None)
        self._feed = MultiExchangeFundingFeed(
            hyperliquid_client=NetworkClient(),
            moondev_client=HyperliquidClient(),
            registry=registry,
            exchanges=exchanges,
            offline=self.app.config.mode == "offline_demo",
        )

    def _tick(self) -> None:
        if not self._feed:
            return
        now = time.monotonic()
        if now >= self._next_fetch:
            self._result = self._feed.fetch_result()
            self._next_fetch = now + self._feed.next_delay(
                self._result.status if self._result else "error"
            )
        self._render()

    def _render(self) -> None:
        self.set_status(_status_line(self._result))
        lines = _build_lines(self._result)
        self.body.update("\n".join(lines))


def _build_lines(result: Optional[FeedResult]) -> List[str]:
    lines: List[str] = []
    payload = result.data if result and isinstance(result.data, dict) else {}
    rows = payload.get("rows") if isinstance(payload, dict) else None
    rows = rows if isinstance(rows, list) else []
    arbitrage = payload.get("arbitrage") if isinstance(payload, dict) else None
    arbitrage = arbitrage if isinstance(arbitrage, list) else []

    lines.append("Funding Heatmap")
    lines.extend(_render_heatmap(rows))
    lines.append("")
    lines.append("Funding Extremes")
    lines.extend(_render_extremes(rows))
    lines.append("")
    lines.append("Arbitrage Comparison")
    lines.extend(_render_arbitrage(arbitrage))
    lines.append("")
    lines.append("Commands: exchange list|add|remove | funding refresh")
    return lines


def _render_heatmap(rows: List[Dict[str, Any]]) -> List[str]:
    if not rows:
        return ["No funding data yet."]
    per_symbol: Dict[str, float] = {}
    for row in rows:
        symbol = str(row.get("symbol") or "?")
        value = row.get("annualized_pct")
        try:
            per_symbol[symbol] = max(per_symbol.get(symbol, 0.0), abs(float(value)))
        except (TypeError, ValueError):
            continue
    if not per_symbol:
        return ["No funding heatmap data yet."]
    max_val = max(per_symbol.values())
    lines: List[str] = []
    for symbol, val in sorted(per_symbol.items(), key=lambda x: x[1], reverse=True)[:8]:
        bar = heat_bar(val, max_val, width=18)
        lines.append(f"{symbol:<6} {bar} {val:.2f}%")
    return lines


def _render_extremes(rows: List[Dict[str, Any]]) -> List[str]:
    if not rows:
        return ["No funding extremes yet."]
    sorted_rows = sorted(
        rows,
        key=lambda r: abs(float(r.get("annualized_pct") or 0.0)),
        reverse=True,
    )
    lines = ["Exchange | Symbol | Annualized | Status"]
    for row in sorted_rows[:8]:
        exchange = row.get("exchange") or "?"
        symbol = row.get("symbol") or "?"
        annual = row.get("annualized_pct")
        status = row.get("status") or "STALE"
        try:
            annual_str = f"{float(annual):+.2f}%"
        except (TypeError, ValueError):
            annual_str = "n/a"
        lines.append(f"{exchange:<10} | {symbol:<6} | {annual_str:<9} | {status}")
    return lines


def _render_arbitrage(arbitrage: List[Dict[str, Any]]) -> List[str]:
    if not arbitrage:
        return ["No arbitrage spreads above threshold."]
    lines = ["Symbol | Spread | Max -> Min"]
    for row in arbitrage[:8]:
        symbol = row.get("symbol") or "?"
        spread = row.get("spread_pct")
        max_ex = row.get("max_exchange") or "?"
        min_ex = row.get("min_exchange") or "?"
        try:
            spread_str = f"{float(spread):.2f}%"
        except (TypeError, ValueError):
            spread_str = "n/a"
        lines.append(f"{symbol:<6} | {spread_str:<7} | {max_ex} -> {min_ex}")
    return lines


def _status_line(result: Optional[FeedResult]) -> str:
    if result is None:
        return "Status: loading | HTTP: pending"
    updated = result.updated_ts_ms
    if updated:
        updated_str = datetime.fromtimestamp(updated / 1000, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
    else:
        updated_str = "unknown"
    stale = ""
    if result.is_lkg and updated:
        stale_s = int((int(time.time() * 1000) - updated) / 1000)
        stale = f" | STALE +{stale_s}s"
    return f"Status: {result.status} | Last update: {updated_str}{stale}"
