"""Funding Arbitrage profile screen (panelized layout)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import time

from textual.containers import Horizontal, Vertical
from textual.widgets import TabbedContent, TabPane

from backend.network import NetworkClient
from backend.storage import DatasetRegistry
from tui.feeds.base import FeedResult, FeedStatus, _as_status
from tui.feeds.funding import MultiExchangeFundingFeed
from tui.feeds.hlp import HlpFeed
from tui.feeds.hyperliquid import HyperliquidClient
from tui.feeds.orderbook_depth import OrderbookDepthFeed
from tui.ui.screens.base import BaseScreen
from tui.widgets.funding_panel import FundingPanel
from tui.widgets.orderbook_panel import OrderbookPanel
from tui.widgets.raw_json_panel import RawJsonPanel
from tickertape.core.alerts import AlertSeverity


FUNDING_EXTREME_RATE = 0.0001


class FundingArbitrageScreen(BaseScreen):
    def __init__(self) -> None:
        super().__init__(
            screen_id="profile_funding_arbitrage",
            title="Funding Arbitrage",
            context="funding_arbitrage",
        )
        self._feed: Optional[MultiExchangeFundingFeed] = None
        self._hlp_feed: Optional[HlpFeed] = None
        self._orderbook_feed: Optional[OrderbookDepthFeed] = None
        self._next_fetch = 0.0
        self._next_hlp_fetch = 0.0
        self._next_orderbook_fetch = 0.0
        self._result: Optional[FeedResult] = None
        self._hlp_result: Optional[FeedResult] = None
        self._orderbook_result: Optional[FeedResult] = None

        self.funding_panel = FundingPanel()
        self.orderbook_panel = OrderbookPanel()
        self.arb_panel = RawJsonPanel("funding_arb", "Arbitrage Signals")
        self.hlp_panel = RawJsonPanel("hlp_summary", "HLP Summary")
        self.orderflow_panel = RawJsonPanel("orderflow_stats", "Orderflow Stats")

        self._panels = [
            self.funding_panel,
            self.orderbook_panel,
            self.arb_panel,
            self.hlp_panel,
            self.orderflow_panel,
        ]

        self._body = Vertical(id="screen_body")
        self.body = self._body
        self._core_row_top = Horizontal(id="funding_row_top", classes="panel-row")
        self._core_row_bottom = Horizontal(id="funding_row_bottom", classes="panel-row")
        self._hlp_row = Horizontal(id="funding_row_hlp", classes="panel-row")
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
                        with TabPane("Core", id="funding_tab_core"):
                            with self._core_row_top:
                                yield self.funding_panel
                            with self._core_row_bottom:
                                yield self.orderbook_panel
                                yield self.arb_panel
                        with TabPane("HLP", id="funding_tab_hlp"):
                            with self._hlp_row:
                                yield self.hlp_panel
                                yield self.orderflow_panel
            yield self.tabbar
            yield self.command_bar

    def on_mount(self) -> None:
        self.set_header("Funding Arbitrage | LIVE")
        self.set_status("Waiting for data...")
        self._build_feed()
        self._apply_panel_palette()
        self.set_interval(1.0, self._tick)

    def on_show(self) -> None:
        super().on_show()
        self._apply_panel_palette()

    def _build_feed(self) -> None:
        registry = DatasetRegistry(path=self.app.config.data_root / "_registry.json")
        exchanges = getattr(self.app.config, "funding_exchanges", None)
        data_client = HyperliquidClient()
        self._feed = MultiExchangeFundingFeed(
            hyperliquid_client=NetworkClient(),
            data_client=data_client,
            registry=registry,
            exchanges=exchanges,
            offline=self.app.config.mode == "offline_demo",
        )
        self._hlp_feed = HlpFeed(
            data_client,
            registry=registry,
            offline=self.app.config.mode == "offline_demo",
            poll_interval=12.0,
        )
        self._orderbook_feed = OrderbookDepthFeed(
            data_client,
            registry=registry,
            offline=self.app.config.mode == "offline_demo",
            poll_interval=8.0,
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
            self._check_alerts()
        if self._hlp_feed and now >= self._next_hlp_fetch:
            self._hlp_result = self._hlp_feed.fetch_result()
            self._next_hlp_fetch = now + self._hlp_feed.next_delay(
                self._hlp_result.status if self._hlp_result else "error"
            )
        if self._orderbook_feed and now >= self._next_orderbook_fetch:
            try:
                symbol = getattr(self.app, "selected_symbol", None)
                if symbol:
                    self._orderbook_feed.set_symbol(symbol)
            except Exception:
                pass
            self._orderbook_result = self._orderbook_feed.fetch_result()
            self._next_orderbook_fetch = now + self._orderbook_feed.next_delay(
                self._orderbook_result.status if self._orderbook_result else "error"
            )
        self._render()

    def _render(self) -> None:
        self.set_status(_status_line(self._result))
        self.funding_panel.update_feed(self._result or FeedResult(status="loading"))
        self.orderbook_panel.update_feed(
            self._orderbook_result or FeedResult(status="loading")
        )

        arb_payload = _extract_arbitrage(self._result)
        self.arb_panel.update_feed(_clone_result(self._result, arb_payload))

        self.hlp_panel.update_feed(self._hlp_result or FeedResult(status="loading"))

        orderflow_payload = _extract_orderflow_stats(self._orderbook_result)
        self.orderflow_panel.update_feed(
            _clone_result(self._orderbook_result, orderflow_payload)
        )

    def _check_alerts(self) -> None:
        if not hasattr(self, "app"):
            return
        if not self.app.is_alert_enabled("funding_extremes"):
            return
        payload = self._result.data if self._result and isinstance(self._result.data, dict) else {}
        rows = payload.get("rows") if isinstance(payload, dict) else None
        if isinstance(rows, list):
            for row in rows[:10]:
                rate = row.get("rate")
                symbol = str(row.get("symbol") or "?")
                exchange = str(row.get("exchange") or "?")
                try:
                    rate_val = float(rate)
                except (TypeError, ValueError):
                    continue
                if abs(rate_val) < FUNDING_EXTREME_RATE:
                    continue
                self.app.emit_alert(
                    alert_type="funding_extremes",
                    severity=AlertSeverity.WARNING,
                    source_feed="funding",
                    payload={
                        "message": f"{exchange} {symbol} rate {rate_val:+.5f}",
                        "symbol": symbol,
                        "exchange": exchange,
                        "rate": rate_val,
                    },
                    key=f"{exchange}:{symbol}",
                    min_interval_ms=60000,
                )
        arbitrage = payload.get("arbitrage") if isinstance(payload, dict) else None
        if isinstance(arbitrage, list) and arbitrage:
            row = arbitrage[0]
            symbol = row.get("symbol") or "?"
            spread = row.get("spread_pct")
            try:
                spread_val = float(spread)
            except (TypeError, ValueError):
                spread_val = None
            if spread_val is not None:
                self.app.emit_alert(
                    alert_type="funding_extremes",
                    severity=AlertSeverity.WARNING,
                    source_feed="funding",
                    payload={
                        "message": f"{symbol} spread {spread_val:.2f}%",
                        "symbol": symbol,
                        "spread_pct": spread_val,
                        "max_exchange": row.get("max_exchange"),
                        "min_exchange": row.get("min_exchange"),
                    },
                    key=f"arb:{symbol}",
                    min_interval_ms=60000,
                )

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


def _status_line(result: Optional[FeedResult]) -> str:
    status = "loading"
    updated = ""
    if result is not None:
        status = _as_status(result.status).value
        if result.updated_ts_ms:
            updated = datetime.fromtimestamp(
                result.updated_ts_ms / 1000, tz=timezone.utc
            ).strftime("%H:%M:%S UTC")
    parts = [f"Funding:{status.upper()}"]
    if updated:
        parts.append(f"Last: {updated}")
    return " | ".join(parts)


def _extract_arbitrage(result: Optional[FeedResult]) -> Dict[str, Any]:
    if not result or not isinstance(result.data, dict):
        return {}
    arbitrage = result.data.get("arbitrage")
    return {"arbitrage": arbitrage} if arbitrage is not None else {}


def _extract_orderflow_stats(result: Optional[FeedResult]) -> Dict[str, Any]:
    if not result or not isinstance(result.data, dict):
        return {}
    return {"orderflow_stats": result.data.get("orderflow_stats")}


def _clone_result(result: Optional[FeedResult], data: Any) -> FeedResult:
    if not result:
        return FeedResult(status=FeedStatus.LOADING, data=data)
    return FeedResult(
        status=result.status,
        data=data,
        error=result.error,
        updated_ts_ms=result.updated_ts_ms,
        is_lkg=result.is_lkg,
    )
