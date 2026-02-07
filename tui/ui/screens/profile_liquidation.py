"""Liquidation Hunter profile screen (panelized layout)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import asyncio
import time

from textual.containers import Horizontal, Vertical
from textual.widgets import TabbedContent, TabPane

from tui.feeds.base import FeedResult, FeedStatus, _as_status
from tui.models.liquidations import LiquidationSnapshot
from tui.ui.screens.base import BaseScreen
from tui.widgets.funding_rates_panel import FundingRatesPanel
from tui.widgets.liquidations_feed_panel import LiquidationsFeedPanel
from tui.widgets.orderbook_panel import OrderbookPanel
from tui.widgets.positions_panel import PositionsPanel
from tui.widgets.raw_json_panel import RawJsonPanel
from tui.widgets.whale_trades_panel import WhaleTradesPanel
from tickertape.core.alerts import AlertSeverity


class LiquidationHunterScreen(BaseScreen):
    def __init__(self) -> None:
        super().__init__(
            screen_id="profile_liquidation",
            title="Liquidation Hunter",
            context="liquidation",
        )
        self._next_liq_fetch = 0.0
        self._next_orderbook_fetch = 0.0
        self._next_whales_fetch = 0.0
        self._next_funding_fetch = 0.0
        self._next_positions_fetch = 0.0
        self._liq_result: Optional[FeedResult] = None
        self._orderbook_result: Optional[FeedResult] = None
        self._whales_result: Optional[FeedResult] = None
        self._funding_result: Optional[FeedResult] = None
        self._positions_result: Optional[FeedResult] = None
        self._market_result: Optional[FeedResult] = None
        # background fetch tasks (prevent blocking the UI event loop)
        self._liq_task: Optional["asyncio.Task"] = None
        self._orderbook_task: Optional["asyncio.Task"] = None
        self._whales_task: Optional["asyncio.Task"] = None
        self._funding_task: Optional["asyncio.Task"] = None
        self._positions_task: Optional["asyncio.Task"] = None
        self._market_task: Optional["asyncio.Task"] = None

        self.liquidations_panel = LiquidationsFeedPanel()
        self.orderbook_panel = OrderbookPanel()
        self.funding_panel = FundingRatesPanel()
        self.positions_panel = PositionsPanel()
        self.whale_panel = WhaleTradesPanel()
        self.stats_panel = RawJsonPanel("liq_stats", "Liquidation Stats")
        self.hip3_panel = RawJsonPanel("liq_hip3", "HIP-3 Snapshot")
        self.combined_panel = RawJsonPanel("liq_combined", "Combined Stats")

        self._panels = [
            self.liquidations_panel,
            self.orderbook_panel,
            self.funding_panel,
            self.positions_panel,
            self.whale_panel,
            self.stats_panel,
            self.hip3_panel,
            self.combined_panel,
        ]

        self._body = Vertical(id="screen_body")
        self.body = self._body
        self._core_row_top = Horizontal(id="liq_row_top", classes="panel-row")
        self._core_row_bottom = Horizontal(id="liq_row_bottom", classes="panel-row")
        self._adv_row_top = Horizontal(id="liq_row_adv_top", classes="panel-row")
        self._adv_row_bottom = Horizontal(id="liq_row_adv_bottom", classes="panel-row")
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
                        with TabPane("Core", id="liq_tab_core"):
                            with self._core_row_top:
                                yield self.liquidations_panel
                                yield self.orderbook_panel
                            with self._core_row_bottom:
                                yield self.funding_panel
                                yield self.positions_panel
                        with TabPane("Advanced", id="liq_tab_advanced"):
                            with self._adv_row_top:
                                yield self.whale_panel
                                yield self.stats_panel
                            with self._adv_row_bottom:
                                yield self.hip3_panel
                                yield self.combined_panel
            yield self.tabbar
            yield self.command_bar

    def on_mount(self) -> None:
        self.set_header("Liquidation Hunter | LIVE")
        self.set_status("Waiting for data...")
        self._apply_panel_palette()
        self.set_interval(1.0, self._tick)

    def on_show(self) -> None:
        super().on_show()
        self._apply_panel_palette()

    def _tick(self) -> None:
        now = time.monotonic()
        provider = getattr(self.app, "provider", None)
        if provider is None:
            return

        if now >= self._next_liq_fetch:
            if not self._liq_task or self._liq_task.done():
                self._liq_task = asyncio.create_task(self._bg_fetch_liquidations())

        if now >= self._next_orderbook_fetch:
            if not self._orderbook_task or self._orderbook_task.done():
                self._orderbook_task = asyncio.create_task(
                    self._bg_fetch_orderbook_depth()
                )

        if now >= self._next_whales_fetch:
            if not self._whales_task or self._whales_task.done():
                self._whales_task = asyncio.create_task(self._bg_fetch_whales())

        if now >= self._next_funding_fetch:
            if not self._funding_task or self._funding_task.done():
                self._funding_task = asyncio.create_task(self._bg_fetch_funding())

        if now >= self._next_positions_fetch:
            if not self._positions_task or self._positions_task.done():
                self._positions_task = asyncio.create_task(self._bg_fetch_positions())

        self._render()

    async def _bg_fetch_liquidations(self) -> None:
        """Run provider.get_liquidations in a thread and update state on completion."""
        if getattr(self, "_app", None) is None:
            return
        provider = getattr(self.app, "provider", None)
        if provider is None:
            return
        result = await asyncio.to_thread(provider.get_liquidations)
        self._liq_result = result
        try:
            status = _as_status(result.status)
            now = time.monotonic()
            self._next_liq_fetch = now + provider.liquidation_next_delay(status.value)
        except Exception:
            pass
        snapshot = _snapshot_from_result(result)
        if snapshot:
            self._maybe_alert_cascade(snapshot)
        self._render()

    async def _bg_fetch_orderbook_depth(self) -> None:
        if getattr(self, "_app", None) is None:
            return
        provider = getattr(self.app, "provider", None)
        if provider is None:
            return
        symbol = getattr(self.app, "selected_symbol", "BTC") or "BTC"
        result = await asyncio.to_thread(provider.get_orderbook_depth, symbol)
        self._orderbook_result = result
        try:
            status = _as_status(result.status)
            now = time.monotonic()
            self._next_orderbook_fetch = now + provider.orderbook_depth_next_delay(
                status.value
            )
        except Exception:
            pass
        self._render()

    async def _bg_fetch_whales(self) -> None:
        if getattr(self, "_app", None) is None:
            return
        provider = getattr(self.app, "provider", None)
        if provider is None or not hasattr(provider, "get_whales"):
            return
        result = await asyncio.to_thread(provider.get_whales)
        self._whales_result = result
        try:
            status = _as_status(result.status)
            now = time.monotonic()
            self._next_whales_fetch = now + provider.whales_next_delay(status.value)
        except Exception:
            pass
        self._render()

    async def _bg_fetch_funding(self) -> None:
        if getattr(self, "_app", None) is None:
            return
        provider = getattr(self.app, "provider", None)
        if provider is None or not hasattr(provider, "get_funding"):
            return
        result = await asyncio.to_thread(provider.get_funding)
        self._funding_result = result
        try:
            status = _as_status(result.status)
            now = time.monotonic()
            self._next_funding_fetch = now + provider.funding_next_delay(status.value)
        except Exception:
            pass
        self._render()

    async def _bg_fetch_positions(self) -> None:
        if getattr(self, "_app", None) is None:
            return
        provider = getattr(self.app, "provider", None)
        if provider is None or not hasattr(provider, "get_positions_snapshot"):
            return
        symbol = getattr(self.app, "selected_symbol", "BTC") or "BTC"
        result = await asyncio.to_thread(provider.get_positions_snapshot, symbol)
        self._positions_result = result
        try:
            status = _as_status(result.status)
            now = time.monotonic()
            self._next_positions_fetch = now + provider.positions_next_delay(status.value)
        except Exception:
            pass
        self._render()

    async def _bg_fetch_market_context(self) -> None:
        """Retained for compatibility with existing tests."""
        if getattr(self, "_app", None) is None:
            return
        provider = getattr(self.app, "provider", None)
        if provider is None:
            return
        symbol = getattr(self.app, "selected_symbol", "BTC") or "BTC"
        result = await asyncio.to_thread(provider.get_market_context, symbol)
        self._market_result = result

    def _render(self) -> None:
        now_ms = int(time.time() * 1000)
        status_line = _status_line(
            {
                "Liq": self._liq_result,
                "Book": self._orderbook_result,
                "Fund": self._funding_result,
                "Pos": self._positions_result,
                "Whale": self._whales_result,
            },
            now_ms,
        )
        self.set_status(status_line)

        liq_result = _ensure_dict_result(self._liq_result)
        self.liquidations_panel.update_feed(liq_result)
        self.orderbook_panel.update_feed(self._orderbook_result or FeedResult(status="loading"))
        self.funding_panel.update_feed(self._funding_result or FeedResult(status="loading"))
        self.positions_panel.update_feed(self._positions_result or FeedResult(status="loading"))
        self.whale_panel.update_feed(self._whales_result or FeedResult(status="loading"))

        snapshot_dict = _snapshot_dict(self._liq_result)
        stats_payload = _extract_stats_payload(snapshot_dict)
        hip3_payload = snapshot_dict.get("hip3") if snapshot_dict else {}
        combined_payload = _extract_combined_payload(snapshot_dict)

        self.stats_panel.update_feed(_clone_result(self._liq_result, stats_payload))
        self.hip3_panel.update_feed(_clone_result(self._liq_result, hip3_payload))
        self.combined_panel.update_feed(_clone_result(self._liq_result, combined_payload))

    def _maybe_alert_cascade(self, snapshot: LiquidationSnapshot) -> None:
        if not hasattr(self, "app"):
            return
        if not self.app.is_alert_enabled("liquidation_cascades"):
            return
        level = str(snapshot.cascade.level or "").upper()
        if level not in {"HIGH", "MED"}:
            return
        self.app.emit_alert(
            alert_type="liquidation_cascades",
            severity=AlertSeverity.CRITICAL if level == "HIGH" else AlertSeverity.WARNING,
            source_feed="liquidations",
            payload={
                "message": f"Cascade risk {level}: {snapshot.cascade.reason}",
                "level": level,
                "score": snapshot.cascade.score,
                "reason": snapshot.cascade.reason,
            },
            key=f"cascade:{level}",
            min_interval_ms=30000,
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


def _ensure_dict_result(result: Optional[FeedResult]) -> FeedResult:
    if not result:
        return FeedResult(status=FeedStatus.LOADING)
    if isinstance(result.data, LiquidationSnapshot):
        return _clone_result(result, result.data.to_dict())
    if isinstance(result.data, dict):
        return result
    return _clone_result(result, {})


def _snapshot_from_result(result: Optional[FeedResult]) -> Optional[LiquidationSnapshot]:
    if not result:
        return None
    if isinstance(result.data, LiquidationSnapshot):
        return result.data
    if isinstance(result.data, dict):
        try:
            return LiquidationSnapshot.from_payload(result.data)
        except Exception:
            return None
    return None


def _snapshot_dict(result: Optional[FeedResult]) -> Dict[str, Any]:
    if not result:
        return {}
    if isinstance(result.data, LiquidationSnapshot):
        return result.data.to_dict()
    if isinstance(result.data, dict):
        return result.data
    return {}


def _extract_stats_payload(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    if not snapshot:
        return {}
    return {
        "timeframes": snapshot.get("timeframes"),
        "rollups": snapshot.get("rollups"),
        "cascade": snapshot.get("cascade"),
        "top_symbols": snapshot.get("top_symbols"),
        "errors": snapshot.get("errors"),
    }


def _extract_combined_payload(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    if not snapshot:
        return {}
    return {
        "combined_stats": snapshot.get("combined_stats"),
        "combined_timeframes": snapshot.get("combined_timeframes"),
        "exchange_stats": snapshot.get("exchange_stats"),
        "exchange_timeframes": snapshot.get("exchange_timeframes"),
    }


def _status_line(results: Dict[str, Optional[FeedResult]], now_ms: int) -> str:
    parts: List[str] = []
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
    else:
        parts.append(f"Now: {datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).strftime('%H:%M:%S UTC')}")
    return " | ".join(parts)
