"""Day Trader profile screen (panelized streaming layout)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import time

from textual.containers import Horizontal, Vertical
from textual.widgets import TabbedContent, TabPane

from tui.feeds.base import FeedResult, FeedStatus, _as_status
from tui.ui.screens.base import BaseScreen
from tui.widgets.market_overview_panel import MarketOverviewPanel
from tui.widgets.orderbook_panel import OrderbookPanel
from tui.widgets.whale_trades_panel import WhaleTradesPanel
from tui.widgets.liquidations_feed_panel import LiquidationsFeedPanel
from tui.widgets.funding_rates_panel import FundingRatesPanel
from tui.widgets.positions_panel import PositionsPanel
from tui.widgets.raw_json_panel import RawJsonPanel
from tickertape.core.alerts import AlertSeverity


DEFAULT_WATCHLIST = ["BTC", "ETH", "SOL"]
WHALE_ALERT_USD = 500_000
ANOMALY_THRESHOLD_PCT = 0.05
VOLUME_SURGE_MULTIPLIER = 3.0
FUNDING_EXTREME_RATE = 0.0001
OI_SPIKE_PCT = 0.20


@dataclass
class DayTraderState:
    watchlist: List[str] = field(default_factory=lambda: list(DEFAULT_WATCHLIST))
    price_history: Dict[str, List[float]] = field(default_factory=dict)
    volume_history: Dict[str, List[float]] = field(default_factory=dict)
    funding_history: Dict[str, List[float]] = field(default_factory=dict)
    oi_history: Dict[str, List[float]] = field(default_factory=dict)


class DayTraderScreen(BaseScreen):
    def __init__(self, provider: Optional[Any] = None) -> None:
        super().__init__(
            screen_id="profile_day_trader",
            title="Day Trader",
            context="day_trader",
        )
        self._provider = provider
        self._market_feed = None
        self._whale_feed = None
        self._liq_feed = None
        self._funding_feed = None
        self._smart_money_feed = None
        self._hlp_feed = None
        self._orderflow_feed = None
        self._hip3_feed = None
        self._positions_feed = None
        self._next_market_fetch = 0.0
        self._next_whale_fetch = 0.0
        self._next_liq_fetch = 0.0
        self._next_funding_fetch = 0.0
        self._next_smart_money_fetch = 0.0
        self._next_hlp_fetch = 0.0
        self._next_orderflow_fetch = 0.0
        self._next_hip3_fetch = 0.0
        self._next_positions_fetch = 0.0
        self._market_result: Optional[FeedResult] = None
        self._whale_result: Optional[FeedResult] = None
        self._liq_result: Optional[FeedResult] = None
        self._funding_result: Optional[FeedResult] = None
        self._smart_money_result: Optional[FeedResult] = None
        self._hlp_result: Optional[FeedResult] = None
        self._orderflow_result: Optional[FeedResult] = None
        self._hip3_result: Optional[FeedResult] = None
        self._positions_result: Optional[FeedResult] = None
        self._state = DayTraderState()
        self._anomaly_thresholds: Dict[str, Dict[str, float]] = {}

        self.market_panel = MarketOverviewPanel()
        self.orderbook_panel = OrderbookPanel()
        self.whale_panel = WhaleTradesPanel()
        self.liquidations_panel = LiquidationsFeedPanel()
        self.funding_panel = FundingRatesPanel()
        self.positions_panel = PositionsPanel()
        self.smart_money_panel = RawJsonPanel("dt_smart_money", "Smart Money")
        self.hlp_panel = RawJsonPanel("dt_hlp", "HLP Summary")
        self.orderflow_panel = RawJsonPanel("dt_orderflow", "Orderflow")
        self.hip3_panel = RawJsonPanel("dt_hip3", "HIP-3 Market")
        self.positions_snapshot_panel = RawJsonPanel(
            "dt_positions_snapshot", "Positions Snapshot"
        )
        self._panels = [
            self.market_panel,
            self.orderbook_panel,
            self.whale_panel,
            self.liquidations_panel,
            self.funding_panel,
            self.positions_panel,
            self.smart_money_panel,
            self.hlp_panel,
            self.orderflow_panel,
            self.hip3_panel,
            self.positions_snapshot_panel,
        ]

        self._body = Vertical(id="screen_body")
        self.body = self._body
        self._row_top = Horizontal(id="dt_row_top", classes="dt-row")
        self._row_mid = Horizontal(id="dt_row_mid", classes="dt-row")
        self._row_bottom = Horizontal(id="dt_row_bottom", classes="dt-row")
        self._signals_row_top = Horizontal(id="dt_row_signals_top", classes="dt-row")
        self._signals_row_mid = Horizontal(id="dt_row_signals_mid", classes="dt-row")
        self._signals_row_bottom = Horizontal(id="dt_row_signals_bottom", classes="dt-row")
        self._tabs = TabbedContent(id="profile_tabs")

    def compose(self):
        with Vertical(id="screen_root"):
            yield self.header
            yield self.status
            yield self.tab_carousel
            with Horizontal(id="content_row"):
                yield self.sidebar
                with self._body:
                    with self._tabs:
                        with TabPane("Core", id="dt_tab_core"):
                            with self._row_top:
                                yield self.market_panel
                                yield self.orderbook_panel
                            with self._row_mid:
                                yield self.whale_panel
                                yield self.liquidations_panel
                            with self._row_bottom:
                                yield self.funding_panel
                                yield self.positions_panel
                        with TabPane("Signals", id="dt_tab_signals"):
                            with self._signals_row_top:
                                yield self.smart_money_panel
                                yield self.orderflow_panel
                            with self._signals_row_mid:
                                yield self.hlp_panel
                                yield self.positions_snapshot_panel
                            with self._signals_row_bottom:
                                yield self.hip3_panel
            yield self.tabbar
            yield self.command_bar

    def on_mount(self) -> None:
        self.set_header("Day Trader | LIVE")
        self.set_status("Waiting for streams...")
        self._sync_watchlist()
        self._wire_provider()
        self._apply_panel_palette()
        self.set_interval(1.0, self._tick)

    def on_show(self) -> None:
        super().on_show()
        self._apply_panel_palette()

    def update_watchlist(self, watchlist: List[str]) -> None:
        if not watchlist:
            return
        self._state.watchlist = [w.upper() for w in watchlist]
        self._apply_watchlist()

    def set_anomaly_thresholds(self, symbol: str, thresholds: Dict[str, float]) -> None:
        normalized = str(symbol or "").upper().strip()
        if not normalized:
            return
        current = self._anomaly_thresholds.get(normalized, {}).copy()
        for key, value in thresholds.items():
            try:
                current[str(key)] = float(value)
            except (TypeError, ValueError):
                continue
        self._anomaly_thresholds[normalized] = current

    def _sync_watchlist(self) -> None:
        getter = getattr(self.app, "get_watchlist", None)
        if getter:
            watchlist = getter()
            if watchlist:
                self._state.watchlist = [w.upper() for w in watchlist]
        self._apply_watchlist()

    def _apply_watchlist(self) -> None:
        if self._market_feed and self._state.watchlist:
            self._market_feed.coin_cycle = list(self._state.watchlist)
            self._market_feed.set_selected_coin(self._state.watchlist[0])
        if self._funding_feed and self._state.watchlist:
            try:
                self._funding_feed.coins = list(self._state.watchlist)
            except Exception:
                pass
        if self.positions_panel:
            self.positions_panel.set_watchlist(self._state.watchlist)
        if self.funding_panel:
            self.funding_panel.set_watchlist(self._state.watchlist)

    def _wire_provider(self) -> None:
        if self._provider is None:
            self._provider = getattr(self.app, "provider", None)
        if not self._provider:
            return
        self._market_feed = getattr(self._provider, "_market_feed", None)
        self._whale_feed = getattr(self._provider, "_whales_feed", None)
        self._liq_feed = getattr(self._provider, "_liquidations_feed", None)
        self._funding_feed = getattr(self._provider, "_funding_feed", None)
        self._smart_money_feed = getattr(self._provider, "_smart_money_feed", None)
        self._hlp_feed = getattr(self._provider, "_hlp_feed", None)
        self._orderflow_feed = getattr(self._provider, "_orderflow_feed", None)
        self._hip3_feed = getattr(self._provider, "_hip3_feed", None)
        self._positions_feed = getattr(self._provider, "_positions_feed", None)

    def _apply_panel_palette(self) -> None:
        try:
            palette = self.app.theme_manager.current()
        except Exception:
            palette = None
        if not palette:
            return
        for panel in self._panels:
            try:
                panel.set_palette(palette)
            except Exception:
                pass

    def _tick(self) -> None:
        now = time.monotonic()
        if not self._provider:
            self._wire_provider()
        if not self._market_feed:
            return

        self._sync_watchlist()

        stream_manager = getattr(self.app, "stream_manager", None)
        use_streams = bool(stream_manager and stream_manager.active)

        self._market_result = self._maybe_update_feed(
            self._market_feed,
            self._market_result,
            now,
            "market",
            use_streams,
        )
        self._whale_result = self._maybe_update_feed(
            self._whale_feed,
            self._whale_result,
            now,
            "whales",
            use_streams,
        )
        self._liq_result = self._maybe_update_feed(
            self._liq_feed,
            self._liq_result,
            now,
            "liquidations",
            use_streams,
        )
        self._funding_result = self._maybe_update_feed(
            self._funding_feed,
            self._funding_result,
            now,
            "funding",
            use_streams,
        )
        if self._orderflow_feed and self._state.watchlist:
            try:
                self._orderflow_feed.set_symbol(self._state.watchlist[0])
            except Exception:
                pass
        self._smart_money_result = self._maybe_update_feed(
            self._smart_money_feed,
            self._smart_money_result,
            now,
            "smart_money",
            use_streams,
        )
        self._hlp_result = self._maybe_update_feed(
            self._hlp_feed,
            self._hlp_result,
            now,
            "hlp",
            use_streams,
        )
        self._orderflow_result = self._maybe_update_feed(
            self._orderflow_feed,
            self._orderflow_result,
            now,
            "orderflow",
            use_streams,
        )
        self._hip3_result = self._maybe_update_feed(
            self._hip3_feed,
            self._hip3_result,
            now,
            "hip3",
            use_streams,
        )
        if self._positions_feed and self._state.watchlist:
            try:
                self._positions_feed.set_symbol(self._state.watchlist[0])
            except Exception:
                pass
        self._positions_result = self._maybe_update_feed(
            self._positions_feed,
            self._positions_result,
            now,
            "positions",
            use_streams,
        )

        self._update_price_history(self._market_result)
        self._check_alerts()
        self._render()

    def _maybe_update_feed(
        self,
        feed: Any,
        current: Optional[FeedResult],
        now: float,
        key: str,
        use_streams: bool,
    ) -> Optional[FeedResult]:
        if feed is None:
            return current

        latest = feed.latest()
        if use_streams:
            current = latest
            should_poll = (
                current is None
                or current.updated_ts_ms is None
                or _as_status(current.status) in {FeedStatus.LOADING, FeedStatus.EMPTY}
            )
            if key == "market" and _market_missing_top_coins(current):
                should_poll = True
            if should_poll and now >= self._next_fetch(key):
                current = feed.fetch_result()
                self._set_next_fetch(key, now, feed, current)
            return current

        if now >= self._next_fetch(key):
            current = feed.fetch_result()
            self._set_next_fetch(key, now, feed, current)
            return current
        return latest

    def _next_fetch(self, key: str) -> float:
        return {
            "market": self._next_market_fetch,
            "whales": self._next_whale_fetch,
            "liquidations": self._next_liq_fetch,
            "funding": self._next_funding_fetch,
            "smart_money": self._next_smart_money_fetch,
            "hlp": self._next_hlp_fetch,
            "orderflow": self._next_orderflow_fetch,
            "hip3": self._next_hip3_fetch,
            "positions": self._next_positions_fetch,
        }.get(key, 0.0)

    def _set_next_fetch(
        self, key: str, now: float, feed: Any, result: Optional[FeedResult]
    ) -> None:
        status = result.status if result else "error"
        delay = feed.next_delay(status)
        if key == "market":
            self._next_market_fetch = now + delay
        elif key == "whales":
            self._next_whale_fetch = now + delay
        elif key == "liquidations":
            self._next_liq_fetch = now + delay
        elif key == "funding":
            self._next_funding_fetch = now + delay
        elif key == "smart_money":
            self._next_smart_money_fetch = now + delay
        elif key == "hlp":
            self._next_hlp_fetch = now + delay
        elif key == "orderflow":
            self._next_orderflow_fetch = now + delay
        elif key == "hip3":
            self._next_hip3_fetch = now + delay
        elif key == "positions":
            self._next_positions_fetch = now + delay

    def _check_alerts(self) -> None:
        if not hasattr(self, "app"):
            return
        if self.app.is_alert_enabled("whale_trades"):
            self._check_whale_trades()
        if self.app.is_alert_enabled("anomaly_spikes"):
            self._check_anomalies()

    def _check_whale_trades(self) -> None:
        result = self._whale_result
        if not result or not isinstance(result.data, dict):
            return
        trades = result.data.get("trades")
        if isinstance(trades, dict):
            trades = trades.get("trades") or trades.get("data") or trades.get("events")
        if not isinstance(trades, list):
            return
        for trade in trades[:10]:
            if not isinstance(trade, dict):
                continue
            symbol = str(trade.get("symbol") or trade.get("coin") or "").upper()
            notional = _coerce_float(
                trade.get("notional_usd")
                or trade.get("value_usd")
                or trade.get("notional")
            )
            if notional is None or notional < WHALE_ALERT_USD:
                continue
            side = str(trade.get("side") or trade.get("direction") or "unknown")
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

    def _check_anomalies(self) -> None:
        for symbol in {w.upper() for w in self._state.watchlist}:
            self._check_price_spike(symbol)
            self._check_volume_surge(symbol)
            self._check_funding_extreme(symbol)
            self._check_oi_spike(symbol)

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
            volume = _coerce_float(entry.get("volume") or entry.get("vol"))
            if volume is not None:
                vol_history = self._state.volume_history.setdefault(symbol, [])
                vol_history.append(volume)
                if len(vol_history) > 30:
                    del vol_history[: len(vol_history) - 30]
            funding = _coerce_float(entry.get("funding"))
            if funding is not None:
                funding_history = self._state.funding_history.setdefault(symbol, [])
                funding_history.append(funding)
                if len(funding_history) > 30:
                    del funding_history[: len(funding_history) - 30]
            open_interest = _coerce_float(entry.get("open_interest"))
            if open_interest is not None:
                oi_history = self._state.oi_history.setdefault(symbol, [])
                oi_history.append(open_interest)
                if len(oi_history) > 30:
                    del oi_history[: len(oi_history) - 30]

    def _threshold(self, symbol: str, key: str, default: float) -> float:
        custom = self._anomaly_thresholds.get(symbol, {})
        try:
            return float(custom.get(key, default))
        except (TypeError, ValueError):
            return default

    def _emit_anomaly(self, symbol: str, key_suffix: str, message: str, payload: Dict[str, Any]) -> None:
        app = getattr(self, "_app", None)
        if app is None:
            try:
                app = self.app
            except Exception:
                return
        body = {"message": message, "symbol": symbol}
        body.update(payload)
        app.emit_alert(
            alert_type="anomaly_spikes",
            severity=AlertSeverity.WARNING,
            source_feed="market_data",
            payload=body,
            key=f"{symbol}:anomaly:{key_suffix}",
            min_interval_ms=60000,
        )

    def _check_price_spike(self, symbol: str) -> None:
        history = self._state.price_history.get(symbol, [])
        if len(history) < 5:
            return
        last = history[-1]
        window = history[-10:] if len(history) >= 10 else history
        baseline = window[:-1] if len(window) > 1 else window
        if not baseline:
            return
        mean = sum(baseline) / len(baseline)
        if mean <= 0:
            return
        deviation = abs(last - mean) / mean
        threshold = self._threshold(symbol, "price_spike_pct", ANOMALY_THRESHOLD_PCT)
        if deviation >= threshold:
            self._emit_anomaly(
                symbol,
                "price_spike",
                f"{symbol} price deviation {deviation*100:.1f}%",
                {"kind": "price_spike", "deviation_pct": deviation * 100, "price": last},
            )

    def _check_volume_surge(self, symbol: str) -> None:
        history = self._state.volume_history.get(symbol, [])
        if len(history) < 5:
            return
        last = history[-1]
        baseline = history[-10:-1] if len(history) >= 10 else history[:-1]
        if not baseline:
            return
        mean = sum(baseline) / len(baseline)
        if mean <= 0:
            return
        ratio = last / mean
        threshold = self._threshold(
            symbol, "volume_surge_mult", VOLUME_SURGE_MULTIPLIER
        )
        if ratio >= threshold:
            self._emit_anomaly(
                symbol,
                "volume_surge",
                f"{symbol} volume surge {ratio:.2f}x",
                {"kind": "volume_surge", "volume_ratio": ratio, "volume": last},
            )

    def _check_funding_extreme(self, symbol: str) -> None:
        history = self._state.funding_history.get(symbol, [])
        if not history:
            return
        last = history[-1]
        threshold = self._threshold(
            symbol, "funding_extreme_rate", FUNDING_EXTREME_RATE
        )
        if abs(last) >= threshold:
            self._emit_anomaly(
                symbol,
                "funding_extreme",
                f"{symbol} funding extreme {last:+.5f}",
                {"kind": "funding_extreme", "funding_rate": last},
            )

    def _check_oi_spike(self, symbol: str) -> None:
        history = self._state.oi_history.get(symbol, [])
        if len(history) < 5:
            return
        last = history[-1]
        baseline = history[-10:-1] if len(history) >= 10 else history[:-1]
        if not baseline:
            return
        mean = sum(baseline) / len(baseline)
        if mean <= 0:
            return
        pct = (last - mean) / mean
        threshold = self._threshold(symbol, "oi_spike_pct", OI_SPIKE_PCT)
        if pct >= threshold:
            self._emit_anomaly(
                symbol,
                "oi_spike",
                f"{symbol} OI spike {pct*100:.1f}%",
                {"kind": "oi_spike", "oi_spike_pct": pct * 100, "open_interest": last},
            )

    def _render(self) -> None:
        stream_manager = getattr(self.app, "stream_manager", None)
        stream_summary = (
            stream_manager.summary() if stream_manager else "WS: n/a"
        )
        status_line = _status_line(
            {
                "Mkt": self._market_result,
                "Whale": self._whale_result,
                "Liq": self._liq_result,
                "Fund": self._funding_result,
                "Smart": self._smart_money_result,
                "HLP": self._hlp_result,
                "Flow": self._orderflow_result,
                "HIP3": self._hip3_result,
                "Pos": self._positions_result,
            },
            stream_summary,
        )
        self.set_status(status_line)

        self.market_panel.update_feed(
            self._market_result or FeedResult(status="loading")
        )
        self.orderbook_panel.update_feed(
            self._market_result or FeedResult(status="loading")
        )
        self.whale_panel.update_feed(
            self._whale_result or FeedResult(status="loading")
        )
        self.liquidations_panel.update_feed(
            self._liq_result or FeedResult(status="loading")
        )
        self.funding_panel.update_feed(
            self._funding_result or FeedResult(status="loading")
        )
        self.positions_panel.update_feed(
            self._market_result or FeedResult(status="loading")
        )
        self.smart_money_panel.update_feed(
            self._smart_money_result or FeedResult(status="loading")
        )
        self.hlp_panel.update_feed(self._hlp_result or FeedResult(status="loading"))
        self.orderflow_panel.update_feed(
            self._orderflow_result or FeedResult(status="loading")
        )
        self.hip3_panel.update_feed(self._hip3_result or FeedResult(status="loading"))
        self.positions_snapshot_panel.update_feed(
            self._positions_result or FeedResult(status="loading")
        )


def _coerce_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _market_missing_top_coins(result: Optional[FeedResult]) -> bool:
    if not result or not isinstance(result.data, dict):
        return True
    top = result.data.get("top_coins")
    return not isinstance(top, list) or not top


def _status_line(results: Dict[str, Optional[FeedResult]], stream_summary: str) -> str:
    parts = [stream_summary]
    latest_ts = 0
    for label, result in results.items():
        if result is None:
            status = "loading"
        else:
            status = _as_status(result.status).value
            if result.updated_ts_ms:
                latest_ts = max(latest_ts, int(result.updated_ts_ms))
        parts.append(f"{label}:{status.upper()}")
    if latest_ts:
        updated_str = datetime.fromtimestamp(latest_ts / 1000, tz=timezone.utc).strftime(
            "%H:%M:%S UTC"
        )
        parts.append(f"Last: {updated_str}")
    return " | ".join(parts)
