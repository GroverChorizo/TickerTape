"""Day Trader profile screen."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import time

from tui.feeds.base import FeedResult
from tui.feeds.hyperliquid import HyperliquidClient, LiquidationsFeed, WhaleTradesFeed
from tui.feeds.market_data import MarketDataFeed
from tui.render.sparkline import sparkline
from tui.ui.screens.base import BaseScreen


DEFAULT_WATCHLIST = ["BTC", "ETH", "SOL"]


@dataclass
class DayTraderState:
    watchlist: List[str] = field(default_factory=lambda: list(DEFAULT_WATCHLIST))
    price_history: Dict[str, List[float]] = field(default_factory=dict)


class DayTraderScreen(BaseScreen):
    def __init__(self, client: Optional[Any] = None) -> None:
        super().__init__(
            screen_id="profile_day_trader",
            title="Day Trader",
            context="day_trader",
        )
        self._client = client or HyperliquidClient()
        self._market_feed: Optional[MarketDataFeed] = None
        self._whale_feed: Optional[WhaleTradesFeed] = None
        self._liq_feed: Optional[LiquidationsFeed] = None
        self._next_market_fetch = 0.0
        self._next_whale_fetch = 0.0
        self._next_liq_fetch = 0.0
        self._market_result: Optional[FeedResult] = None
        self._whale_result: Optional[FeedResult] = None
        self._liq_result: Optional[FeedResult] = None
        self._state = DayTraderState()

    def on_mount(self) -> None:
        self.set_header("Day Trader | LIVE")
        self.set_status("Waiting for data...")
        self._sync_watchlist()
        self._build_feeds()
        self.set_interval(1.0, self._tick)

    def on_unmount(self) -> None:
        try:
            if hasattr(self._client, "close"):
                self._client.close()
        except Exception:
            pass

    def update_watchlist(self, watchlist: List[str]) -> None:
        if not watchlist:
            return
        self._state.watchlist = [w.upper() for w in watchlist]
        if self._market_feed:
            self._market_feed.coin_cycle = list(self._state.watchlist)
            self._market_feed.selected_coin = self._state.watchlist[0]

    def _sync_watchlist(self) -> None:
        getter = getattr(self.app, "get_watchlist", None)
        if getter:
            watchlist = getter()
            if watchlist:
                self._state.watchlist = [w.upper() for w in watchlist]

    def _build_feeds(self) -> None:
        watchlist = list(self._state.watchlist)
        if not watchlist:
            watchlist = list(DEFAULT_WATCHLIST)
        self._market_feed = MarketDataFeed(
            self._client,
            poll_interval=1.5,
            offline=getattr(self.app, "config", None).mode == "offline_demo",
            selected_coin=watchlist[0],
            coin_cycle=watchlist,
        )
        self._whale_feed = WhaleTradesFeed(
            self._client,
            poll_interval=4.0,
            offline=getattr(self.app, "config", None).mode == "offline_demo",
        )
        self._liq_feed = LiquidationsFeed(
            self._client,
            poll_interval=5.0,
            offline=getattr(self.app, "config", None).mode == "offline_demo",
        )

    def _tick(self) -> None:
        now = time.monotonic()
        if not self._market_feed or not self._whale_feed or not self._liq_feed:
            return
        self._sync_watchlist()

        if now >= self._next_market_fetch:
            self._market_result = self._market_feed.fetch_result()
            self._next_market_fetch = now + self._market_feed.next_delay(
                self._market_result.status
            )
            self._update_price_history(self._market_result)

        if now >= self._next_whale_fetch:
            self._whale_result = self._whale_feed.fetch_result()
            self._next_whale_fetch = now + self._whale_feed.next_delay(
                self._whale_result.status
            )

        if now >= self._next_liq_fetch:
            self._liq_result = self._liq_feed.fetch_result()
            self._next_liq_fetch = now + self._liq_feed.next_delay(
                self._liq_result.status
            )

        self._render()

    def _update_price_history(self, result: Optional[FeedResult]) -> None:
        if not result or not isinstance(result.data, dict):
            return
        top = result.data.get("top_coins")
        if not isinstance(top, list):
            return
        watch = {w.upper() for w in self._state.watchlist}
        for entry in top:
            if not isinstance(entry, dict):
                continue
            symbol = str(entry.get("symbol") or "").upper()
            if symbol not in watch:
                continue
            try:
                price = float(entry.get("last"))
            except (TypeError, ValueError):
                continue
            history = self._state.price_history.setdefault(symbol, [])
            history.append(price)
            if len(history) > 30:
                del history[: len(history) - 30]

    def _render(self) -> None:
        now_ms = int(time.time() * 1000)
        status = _status_line(self._market_result, now_ms)
        self.set_status(status)
        lines = _build_lines(
            self._state,
            self._market_result,
            self._whale_result,
            self._liq_result,
        )
        self.body.update("\n".join(lines))


def _build_lines(
    state: DayTraderState,
    market_result: Optional[FeedResult],
    whale_result: Optional[FeedResult],
    liq_result: Optional[FeedResult],
) -> List[str]:
    lines: List[str] = []
    lines.append("Price Chart")
    lines.extend(_render_price_chart(state))
    lines.append("")
    lines.append("Top Positions (proxy: open interest)")
    lines.extend(_render_positions(market_result, state.watchlist))
    lines.append("")
    lines.append("Whale Flow")
    lines.extend(_render_whale_flow(whale_result))
    lines.append("")
    lines.append("Liquidation Stats")
    lines.extend(_render_liquidations(liq_result))
    return lines


def _render_price_chart(state: DayTraderState) -> List[str]:
    lines: List[str] = []
    if not state.watchlist:
        return ["No watchlist configured."]
    for symbol in state.watchlist:
        history = state.price_history.get(symbol, [])
        spark = sparkline(history, width=20)
        last = f"{history[-1]:,.2f}" if history else "n/a"
        lines.append(f"{symbol:<6} {spark} {last}")
    return lines


def _render_positions(
    market_result: Optional[FeedResult], watchlist: List[str]
) -> List[str]:
    if not market_result or not isinstance(market_result.data, dict):
        return ["Positions data not available."]
    top = market_result.data.get("top_coins")
    if not isinstance(top, list):
        return ["Positions data not available."]
    watch = {w.upper() for w in watchlist}
    lines: List[str] = ["Symbol | OI | Funding"]
    for entry in top:
        if not isinstance(entry, dict):
            continue
        symbol = str(entry.get("symbol") or "").upper()
        if symbol not in watch:
            continue
        oi = _fmt_num(entry.get("open_interest"))
        funding = _fmt_num(entry.get("funding"))
        lines.append(f"{symbol:<6} | {oi:<8} | {funding}")
    if len(lines) == 1:
        lines.append("No watchlist matches in top coins.")
    return lines


def _render_whale_flow(result: Optional[FeedResult]) -> List[str]:
    if not result or not isinstance(result.data, dict):
        return ["No whale flow data yet."]
    trades = result.data.get("trades")
    if isinstance(trades, dict):
        trades = trades.get("trades") or trades.get("data") or trades.get("events")
    if not isinstance(trades, list):
        return ["No whale trades available."]
    buys = sells = 0
    lines: List[str] = []
    for entry in trades[:10]:
        if not isinstance(entry, dict):
            continue
        side = str(entry.get("side") or entry.get("direction") or "?").lower()
        if "buy" in side or "long" in side:
            buys += 1
        elif "sell" in side or "short" in side:
            sells += 1
        symbol = entry.get("symbol") or entry.get("coin") or "?"
        size = entry.get("size") or entry.get("amount") or "?"
        price = entry.get("price") or "?"
        lines.append(f"{symbol} {side:<5} size={size} price={price}")
    lines.insert(0, f"Buys: {buys} | Sells: {sells}")
    return lines


def _render_liquidations(result: Optional[FeedResult]) -> List[str]:
    if not result or not isinstance(result.data, dict):
        return ["No liquidation stats yet."]
    snapshot = result.data.get("snapshot")
    if not isinstance(snapshot, dict):
        return ["No liquidation stats yet."]
    stats = (
        snapshot.get("stats") if isinstance(snapshot.get("stats"), dict) else snapshot
    )
    total = _fmt_num(stats.get("total_value_usd") or stats.get("total_usd"))
    count = stats.get("total_count") or stats.get("count")
    long_count = stats.get("long_count") or stats.get("longs")
    short_count = stats.get("short_count") or stats.get("shorts")
    return [
        f"Total notional: {total}",
        f"Count: {count if count is not None else 'n/a'} | Long: {long_count or 'n/a'} | Short: {short_count or 'n/a'}",
    ]


def _fmt_num(value: Any) -> str:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if abs(num) >= 1000:
        return f"{num:,.2f}"
    return f"{num:.4f}"


def _status_line(result: Optional[FeedResult], now_ms: int) -> str:
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
        stale_s = int((now_ms - updated) / 1000)
        stale = f" | STALE +{stale_s}s"
    return f"Status: {result.status} | Last update: {updated_str}{stale}"
