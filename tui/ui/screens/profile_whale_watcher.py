"""Whale Watcher profile screen (panelized layout)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional
import time

from textual.containers import Horizontal, Vertical
from textual.widgets import TabbedContent, TabPane

from tui.feeds.base import FeedResult, FeedStatus
from tui.feeds.hyperliquid import HyperliquidClient, WhaleTradesFeed
from tui.feeds.smart_money import SmartMoneyFeed
from tui.feeds.whale_insights import WhaleInsightsFeed
from tui.ui.screens.base import BaseScreen
from tui.widgets.raw_json_panel import RawJsonPanel
from tui.widgets.wallet_panel import WalletDetailPanel, WalletPanel, WalletSelected, WalletsDiscovered
from tui.widgets.whale_panel import WhalePanel
from tickertape.core.alerts import AlertSeverity
from backend.storage import DatasetRegistry


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
        registry = DatasetRegistry()
        self._smart_feed = SmartMoneyFeed(self._client, registry=registry)
        self._insights_feed = WhaleInsightsFeed(self._client, registry=registry)
        self._next_fetch = 0.0
        self._next_smart_fetch = 0.0
        self._next_insights_fetch = 0.0
        self._result: Optional[FeedResult] = None
        self._smart_result: Optional[FeedResult] = None
        self._insights_result: Optional[FeedResult] = None
        self._filter = WhaleFilter()

        self.whale_panel = WhalePanel()
        self.wallet_panel = WalletPanel()
        self.wallet_panel.id = "wallets"
        self.wallet_panel.add_class("panel")
        self.wallet_detail_panel = WalletDetailPanel()
        self.insights_panel = RawJsonPanel("whale_insights", "Whale Insights")
        self.smart_money_panel = RawJsonPanel("smart_money", "Smart Money")
        self.whale_addresses_panel = RawJsonPanel(
            "whale_insights_alt", "Whale Addresses"
        )

        self._panels = [
            self.whale_panel,
            self.wallet_detail_panel,
            self.insights_panel,
            self.smart_money_panel,
            self.whale_addresses_panel,
        ]

        self._body = Vertical(id="screen_body")
        self.body = self._body
        self._core_row_top = Horizontal(id="whale_row_top", classes="panel-row")
        self._core_row_bottom = Horizontal(id="whale_row_bottom", classes="panel-row")
        self._signals_row_top = Horizontal(id="whale_row_signals", classes="panel-row")
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
                        with TabPane("Core", id="whale_tab_core"):
                            with self._core_row_top:
                                yield self.whale_panel
                                yield self.wallet_panel
                            with self._core_row_bottom:
                                yield self.wallet_detail_panel
                                yield self.insights_panel
                        with TabPane("Signals", id="whale_tab_signals"):
                            with self._signals_row_top:
                                yield self.smart_money_panel
                                yield self.whale_addresses_panel
            yield self.tabbar
            yield self.command_bar

    def on_mount(self) -> None:
        self.set_header("Whale Watcher | LIVE")
        self.set_status("Waiting for data...")
        self._apply_panel_palette()
        self.set_interval(1.0, self._tick)

    def on_show(self) -> None:
        super().on_show()
        self._apply_panel_palette()

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
        self.whale_panel.min_notional = self._filter.min_notional

    def on_wallets_discovered(self, message: WalletsDiscovered) -> None:
        self.wallet_panel.update_wallets(message.addresses, message.source)
        if hasattr(self, "app"):
            try:
                self.app.set_wallets(message.addresses)
            except Exception:
                pass

    def on_wallet_selected(self, message: WalletSelected) -> None:
        self.wallet_detail_panel.update_wallet(message.address, message.source)

    def _tick(self) -> None:
        now = time.monotonic()
        if now >= self._next_fetch:
            self._result = self._feed.fetch_result()
            self._next_fetch = now + self._feed.next_delay(
                self._result.status if self._result else "error"
            )
            self._check_alerts()
        if now >= self._next_smart_fetch:
            self._smart_result = self._smart_feed.fetch_result()
            self._next_smart_fetch = now + self._smart_feed.next_delay(
                self._smart_result.status if self._smart_result else "error"
            )
        if now >= self._next_insights_fetch:
            self._insights_result = self._insights_feed.fetch_result()
            self._next_insights_fetch = now + self._insights_feed.next_delay(
                self._insights_result.status if self._insights_result else "error"
            )
        self._render()

    def _render(self) -> None:
        filtered_result = self._filtered_result(self._result)
        if filtered_result:
            self.whale_panel.update_feed(filtered_result)
            wallets = _extract_wallets_from_result(filtered_result)
            if wallets:
                try:
                    self.wallet_panel.update_wallets(wallets, "whales")
                except Exception:
                    pass
                if hasattr(self, "app"):
                    try:
                        self.app.set_wallets(wallets)
                    except Exception:
                        pass
        if self._smart_result:
            self.smart_money_panel.update_feed(self._smart_result)
        if self._insights_result:
            self.insights_panel.update_feed(self._insights_result)
            addresses = _extract_whale_addresses(self._insights_result.data)
            self.whale_addresses_panel.update_feed(
                _clone_result(self._insights_result, {"whale_addresses": addresses})
            )
        else:
            self.smart_money_panel.update_feed(FeedResult(status=FeedStatus.LOADING))
            self.insights_panel.update_feed(FeedResult(status=FeedStatus.LOADING))
            self.whale_addresses_panel.update_feed(FeedResult(status=FeedStatus.LOADING))

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

    def _filtered_result(self, result: Optional[FeedResult]) -> Optional[FeedResult]:
        if not result or not isinstance(result.data, dict):
            return result
        trades = _extract_trades(result)
        if not trades:
            return result
        filtered = _filter_trades(
            trades,
            side=self._filter.side,
            min_notional=self._filter.min_notional,
        )
        payload = dict(result.data)
        payload["trades"] = filtered
        return _clone_result(result, payload)

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


def _clone_result(result: FeedResult, data: Any) -> FeedResult:
    return FeedResult(
        status=result.status,
        data=data,
        error=result.error,
        updated_ts_ms=result.updated_ts_ms,
        is_lkg=result.is_lkg,
    )


def _extract_trades(result: Optional[FeedResult]) -> List[dict]:
    if not result or not isinstance(result.data, dict):
        return []
    trades = result.data.get("trades")
    if isinstance(trades, dict):
        trades = trades.get("trades") or trades.get("data") or trades.get("events")
    if not isinstance(trades, list):
        return []
    return [trade for trade in trades if isinstance(trade, dict)]


def _filter_trades(trades: List[dict], *, side: str, min_notional: float) -> List[dict]:
    side = (side or "all").lower()
    filtered: List[dict] = []
    for trade in trades:
        notional = _trade_notional(trade)
        if notional < min_notional:
            continue
        trade_side = _trade_side(trade)
        if side != "all" and not _side_matches(trade_side, side):
            continue
        filtered.append(trade)
    return filtered


def _side_matches(trade_side: str, filter_side: str) -> bool:
    trade_side = trade_side.lower()
    filter_side = filter_side.lower()
    if filter_side in {"buy", "long"}:
        return trade_side in {"buy", "long"}
    if filter_side in {"sell", "short"}:
        return trade_side in {"sell", "short"}
    return True


def _trade_symbol(trade: dict) -> str:
    return str(trade.get("symbol") or trade.get("coin") or "?")


def _trade_side(trade: dict) -> str:
    return str(trade.get("side") or trade.get("direction") or "unknown").lower()


def _trade_notional(trade: dict) -> float:
    notional = trade.get("notional_usd") or trade.get("value_usd") or trade.get("notional")
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


def _extract_wallets_from_result(result: FeedResult) -> List[str]:
    trades = _extract_trades(result)
    wallets: List[str] = []
    for trade in trades:
        for key in ("wallet", "wallet_address", "address"):
            value = trade.get(key)
            if isinstance(value, str) and value:
                wallets.append(value)
    return list(dict.fromkeys(wallets))


def _extract_whale_addresses(payload: Any) -> List[str]:
    if not isinstance(payload, dict):
        return []
    addresses = payload.get("whale_addresses")
    if isinstance(addresses, list):
        return [str(addr) for addr in addresses if addr]
    return []
