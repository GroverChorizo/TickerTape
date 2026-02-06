"""Whale Watcher profile screen."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import time

from tui.feeds.base import FeedResult
from tui.feeds.hyperliquid import HyperliquidClient, WhaleTradesFeed
from tui.render.sparkline import heat_bar
from tui.ui.screens.base import BaseScreen
from tickertape.core.alerts import AlertSeverity


@dataclass
class WhaleFilter:
    side: str = "all"
    min_notional: float = 25_000.0


WHALE_ALERT_USD = 500_000


class WhaleWatcherScreen(BaseScreen):
    def __init__(self, client: Optional[Any] = None) -> None:
        super().__init__(
            screen_id="profile_whale_watcher",
            title="Whale Watcher",
            context="whale_watcher",
        )
        self._client = client or HyperliquidClient()
        self._feed = WhaleTradesFeed(self._client, poll_interval=4.0)
        self._next_fetch = 0.0
        self._result: Optional[FeedResult] = None
        self._filter = WhaleFilter()

    def on_mount(self) -> None:
        self.set_header("Whale Watcher | LIVE")
        self.set_status("Waiting for data...")
        self.set_interval(1.0, self._tick)

    def on_unmount(self) -> None:
        try:
            if hasattr(self._client, "close"):
                self._client.close()
        except Exception:
            pass

    def update_filter(self, side: str, min_notional: float) -> None:
        if side:
            self._filter.side = side
        self._filter.min_notional = max(min_notional, 0.0)

    def _tick(self) -> None:
        now = time.monotonic()
        if now >= self._next_fetch:
            self._result = self._feed.fetch_result()
            self._next_fetch = now + self._feed.next_delay(
                self._result.status if self._result else "error"
            )
            self._check_alerts()
        self._render()

    def _check_alerts(self) -> None:
        if not hasattr(self, "app"):
            return
        if not self.app.is_alert_enabled("whale_trades"):
            return
        trades = _extract_trades(self._result)
        for trade in trades[:10]:
            symbol = _trade_symbol(trade).upper()
            side = _trade_side(trade)
            notional = _trade_notional(trade)
            if notional < WHALE_ALERT_USD:
                continue
            self.app.emit_alert(
                alert_type="whale_trades",
                severity=AlertSeverity.WARNING,
                source_feed="whales",
                payload={
                    "message": f"{symbol} {side} ${notional:,.0f}",
                    "symbol": symbol,
                    "side": side,
                    "notional_usd": notional,
                },
                key=f"{symbol}:{side}",
                min_interval_ms=30000,
            )

    def _render(self) -> None:
        lines, wallets = _build_lines(self._result, self._filter)
        updater = getattr(self.app, "set_wallets", None)
        if updater:
            updater(wallets)
        self.body.update("\n".join(lines))


def _build_lines(
    result: Optional[FeedResult], whale_filter: WhaleFilter
) -> tuple[List[str], List[str]]:
    lines: List[str] = []
    wallets: List[str] = []
    lines.append("Whale Trade List")
    trades = _extract_trades(result)
    filtered = [
        trade
        for trade in trades
        if _trade_notional(trade) >= whale_filter.min_notional
        and _side_matches(trade, whale_filter.side)
    ]
    for trade in filtered[:10]:
        symbol = _trade_symbol(trade)
        side = _trade_side(trade)
        size = trade.get("size") or trade.get("amount") or trade.get("qty") or "?"
        price = trade.get("price") or trade.get("px") or "?"
        wallet = _trade_wallet(trade)
        if wallet:
            wallets.append(wallet)
        lines.append(f"{symbol} {side:<5} size={size} price={price}")
    if not filtered:
        lines.append("No whale trades match current filter.")

    lines.append("")
    lines.append("Directional Flow")
    lines.extend(_render_flow_bars(filtered))

    lines.append("")
    lines.append("Whale Heatmap")
    lines.extend(_render_heatmap(filtered))

    lines.append("")
    lines.append("Wallets")
    unique_wallets = list(dict.fromkeys(wallets))
    if unique_wallets:
        for idx, addr in enumerate(unique_wallets[:8], start=1):
            lines.append(f"{idx:>2}. {addr}")
    else:
        lines.append("No wallet addresses available.")

    lines.append("")
    lines.append(
        "Commands: whalefilter side=<buy|sell|all> min=<notional> | wallet <#|address>"
    )
    return lines, unique_wallets


def _render_flow_bars(trades: List[Dict[str, Any]]) -> List[str]:
    buys = 0
    sells = 0
    for trade in trades:
        side = _trade_side(trade)
        if side in {"buy", "long"}:
            buys += 1
        elif side in {"sell", "short"}:
            sells += 1
    max_count = max(buys, sells, 1)
    lines = [
        f"Buys : {heat_bar(buys, max_count, width=12)} {buys}",
        f"Sells: {heat_bar(sells, max_count, width=12)} {sells}",
    ]
    return lines


def _render_heatmap(trades: List[Dict[str, Any]]) -> List[str]:
    totals: Dict[str, float] = {}
    for trade in trades:
        symbol = _trade_symbol(trade)
        totals[symbol] = totals.get(symbol, 0.0) + _trade_notional(trade)
    if not totals:
        return ["No whale heatmap data yet."]
    max_val = max(totals.values())
    lines: List[str] = []
    for symbol, total in sorted(totals.items(), key=lambda x: x[1], reverse=True)[:8]:
        bar = heat_bar(total, max_val, width=16)
        lines.append(f"{symbol:<6} {bar} ${total:,.0f}")
    return lines


def _extract_trades(result: Optional[FeedResult]) -> List[Dict[str, Any]]:
    if not result or not isinstance(result.data, dict):
        return []
    trades = result.data.get("trades")
    if isinstance(trades, dict):
        trades = trades.get("trades") or trades.get("data") or trades.get("events")
    if isinstance(trades, list):
        return [t for t in trades if isinstance(t, dict)]
    return []


def _trade_side(trade: Dict[str, Any]) -> str:
    side = str(trade.get("side") or trade.get("direction") or "").lower()
    if "buy" in side or "long" in side:
        return "buy"
    if "sell" in side or "short" in side:
        return "sell"
    return "?"


def _side_matches(trade: Dict[str, Any], side_filter: str) -> bool:
    if side_filter == "all":
        return True
    side = _trade_side(trade)
    return side == side_filter


def _trade_symbol(trade: Dict[str, Any]) -> str:
    return str(trade.get("symbol") or trade.get("coin") or "?")


def _trade_wallet(trade: Dict[str, Any]) -> Optional[str]:
    wallet = trade.get("wallet") or trade.get("wallet_address") or trade.get("address")
    return str(wallet) if isinstance(wallet, str) and wallet else None


def _trade_notional(trade: Dict[str, Any]) -> float:
    notional = trade.get("notional") or trade.get("value") or trade.get("usd_value")
    if notional is not None:
        try:
            return float(notional)
        except (TypeError, ValueError):
            return 0.0
    size = trade.get("size") or trade.get("amount") or trade.get("qty")
    price = trade.get("price") or trade.get("px")
    try:
        return float(size) * float(price)
    except (TypeError, ValueError):
        return 0.0
