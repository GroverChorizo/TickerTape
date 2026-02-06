"""Liquidation Hunter profile screen."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import time
import asyncio

from tui.ui.screens.base import BaseScreen
from tui.models.liquidations import LiquidationSnapshot
from tui.models.market import MarketContext
from tui.feeds.base import FeedResult, FeedStatus, _as_status
from tui.render.sparkline import sparkline, heat_bar
from backend.query_helpers import load_latest_snapshot
from backend.storage import DatasetRegistry
from tickertape.core.alerts import AlertSeverity


class LiquidationHunterScreen(BaseScreen):
    def __init__(self) -> None:
        super().__init__(
            screen_id="profile_liquidation",
            title="Liquidation Hunter",
            context="liquidation",
        )
        self._next_liq_fetch = 0.0
        self._next_market_fetch = 0.0
        self._next_positions_fetch = 0.0
        self._next_whales_fetch = 0.0
        self._next_funding_fetch = 0.0
        self._liq_result: Optional[FeedResult] = None
        self._market_result: Optional[FeedResult] = None
        self._whales_result: Optional[FeedResult] = None
        self._funding_result: Optional[FeedResult] = None
        self._positions_snapshot: Optional[Dict[str, Any]] = None
        # background fetch tasks (prevent blocking the UI event loop)
        self._liq_task: Optional["asyncio.Task"] = None
        self._market_task: Optional["asyncio.Task"] = None
        self._whales_task: Optional["asyncio.Task"] = None
        self._funding_task: Optional["asyncio.Task"] = None
        # diagnostics: event-loop lag in milliseconds
        self._loop_lag_ms: int = 0
        self._last_loop_tick: float | None = None

    def on_mount(self) -> None:
        self.set_header("Liquidation Hunter | LIVE")
        self.set_status("Waiting for data...")
        # UI widgets (mounted into the content row) — added for better visual layout
        try:
            from tui.ui.widgets.orderbook_imbalance import OrderbookImbalanceWidget
            from tui.ui.widgets.funding_rates import FundingRatesWidget
            from tui.ui.widgets.whale_positions import WhalePositionsWidget

            self._orderbook_widget = OrderbookImbalanceWidget(id="orderbook_imbalance")
            self._funding_widget = FundingRatesWidget(id="funding_rates")
            self._whales_widget = WhalePositionsWidget(id="whale_positions")
            # mount widgets into the content area alongside the body (best-effort)
            try:
                content = self.query_one("#content_row")
                content.mount(self._orderbook_widget)
                content.mount(self._funding_widget)
                content.mount(self._whales_widget)
            except Exception:
                # fallback: keep rendering into body if mount fails
                self._orderbook_widget = None
                self._funding_widget = None
                self._whales_widget = None
        except Exception:
            self._orderbook_widget = None
            self._funding_widget = None
            self._whales_widget = None

        self.set_interval(1.0, self._tick)

    def _tick(self) -> None:
        self._measure_loop_lag()
        now = time.monotonic()
        provider = getattr(self.app, "provider", None)
        store = getattr(self.app, "state_store", None)
        if provider is None or store is None:
            return

        # Non-blocking: schedule background fetch for liquidations (if not already running)
        if now >= self._next_liq_fetch:
            if not self._liq_task or self._liq_task.done():
                try:
                    loop = asyncio.get_running_loop()
                    self._liq_task = loop.create_task(self._bg_fetch_liquidations())
                except Exception:
                    # best-effort: fall back to synchronous call if loop unavailable
                    try:
                        result = provider.get_liquidations()
                        self._liq_result = result
                        status = _as_status(result.status)
                        self._next_liq_fetch = now + provider.liquidation_next_delay(status.value)
                        if isinstance(result.data, LiquidationSnapshot):
                            store.update_snapshot(
                                "liquidation_hunter",
                                "snapshot",
                                result.data,
                                ts_ms=result.updated_ts_ms,
                            )
                            self._maybe_alert_cascade(result.data)
                            cache_snapshot = getattr(self.app, "cache_snapshot", None)
                            if cache_snapshot:
                                cache_snapshot("liquidation_hunter", "snapshot", result.data)
                        if result.error:
                            store.set_error("liquidation_hunter", "snapshot", result.error)
                    except Exception:
                        pass

        # Non-blocking: schedule background fetch for market context
        if now >= self._next_market_fetch:
            if not self._market_task or self._market_task.done():
                try:
                    loop = asyncio.get_running_loop()
                    self._market_task = loop.create_task(self._bg_fetch_market_context())
                except Exception:
                    # fallback synchronous path
                    try:
                        symbol = getattr(self.app, "selected_symbol", "BTC") or "BTC"
                        result = provider.get_market_context(symbol)
                        self._market_result = result
                        status = _as_status(result.status)
                        self._next_market_fetch = now + provider.market_next_delay(status.value)
                        # push into widgets (synchronous fallback)
                        try:
                            if hasattr(self, "_orderbook_widget") and self._orderbook_widget:
                                payload = None
                                if isinstance(result.data, dict):
                                    payload = result.data.get("orderbook") or result.data.get("tick") or result.data
                                elif hasattr(result.data, "__dict__"):
                                    payload = getattr(result.data, "orderbook", None) or getattr(result.data, "tick", None)
                                if payload:
                                    try:
                                        self._orderbook_widget.update_from_orderbook(payload)
                                    except Exception:
                                        pass
                                    try:
                                        if hasattr(self, "_funding_widget") and self._funding_widget:
                                            fw = payload.get("funding") if isinstance(payload, dict) else None
                                            if fw:
                                                self._funding_widget.update_from_funding({"funding": fw})
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                    except Exception:
                        pass
        # also update whales widget from provider-level feed snapshot if available
        try:
            if hasattr(self, "_whales_widget") and self._whales_widget:
                wf = getattr(self.app, "_whales_snapshot", None) or None
                if wf:
                    self._whales_widget.update_from_whales(wf)
        except Exception:
            pass

        # fetch whales feed in background (for whale positions widget)
        if now >= self._next_whales_fetch and hasattr(provider, "get_whales"):
            if not self._whales_task or self._whales_task.done():
                try:
                    loop = asyncio.get_running_loop()
                    self._whales_task = loop.create_task(self._bg_fetch_whales())
                except Exception:
                    try:
                        result = provider.get_whales()
                        self._whales_result = result
                        status = _as_status(result.status)
                        self._next_whales_fetch = now + provider.whales_next_delay(status.value)
                        self._update_whales_widget(result)
                    except Exception:
                        pass

        # fetch funding feed in background (for funding rates widget)
        if now >= self._next_funding_fetch and hasattr(provider, "get_funding"):
            if not self._funding_task or self._funding_task.done():
                try:
                    loop = asyncio.get_running_loop()
                    self._funding_task = loop.create_task(self._bg_fetch_funding())
                except Exception:
                    try:
                        result = provider.get_funding()
                        self._funding_result = result
                        status = _as_status(result.status)
                        self._next_funding_fetch = now + provider.funding_next_delay(status.value)
                        self._update_funding_widget(result)
                    except Exception:
                        pass

        if now >= self._next_positions_fetch:
            self._positions_snapshot = _load_positions_snapshot(self.app)
            self._next_positions_fetch = now + 10.0

        self._render()

    async def _bg_fetch_liquidations(self) -> None:
        """Run provider.get_liquidations in a thread and update state on completion.
        This ensures the UI event loop is never blocked by slow network or parsing.
        """
        try:
            if getattr(self, "_app", None) is None:
                return
            provider = getattr(self.app, "provider", None)
            store = getattr(self.app, "state_store", None)
            if provider is None or store is None:
                return
            # call the sync provider in a thread
            result = await asyncio.to_thread(provider.get_liquidations)
            # update state on the UI loop
            self._liq_result = result
            try:
                status = _as_status(result.status)
                now = time.monotonic()
                self._next_liq_fetch = now + provider.liquidation_next_delay(status.value)
            except Exception:
                pass
            if isinstance(result.data, LiquidationSnapshot):
                try:
                    store.update_snapshot(
                        "liquidation_hunter",
                        "snapshot",
                        result.data,
                        ts_ms=result.updated_ts_ms,
                    )
                    self._maybe_alert_cascade(result.data)
                    cache_snapshot = getattr(self.app, "cache_snapshot", None)
                    if cache_snapshot:
                        cache_snapshot("liquidation_hunter", "snapshot", result.data)
                except Exception:
                    pass
            if result.error:
                try:
                    store.set_error("liquidation_hunter", "snapshot", result.error)
                except Exception:
                    pass
            # re-render with new data
            try:
                self._render()
            except Exception:
                pass
        except Exception:
            # swallow background errors — UI remains responsive
            return

    async def _bg_fetch_market_context(self) -> None:
        """Fetch market context in a background thread and push payloads into widgets."""
        try:
            if getattr(self, "_app", None) is None:
                return
            provider = getattr(self.app, "provider", None)
            if provider is None:
                return
            symbol = getattr(self.app, "selected_symbol", "BTC") or "BTC"
            result = await asyncio.to_thread(provider.get_market_context, symbol)
            self._market_result = result
            try:
                status = _as_status(result.status)
                now = time.monotonic()
                self._next_market_fetch = now + provider.market_next_delay(status.value)
            except Exception:
                pass
            # push into mounted widgets (non-blocking, defensive)
            try:
                payload = None
                if isinstance(result.data, dict):
                    payload = result.data.get("orderbook") or result.data.get("tick") or result.data
                elif hasattr(result.data, "__dict__"):
                    payload = getattr(result.data, "orderbook", None) or getattr(result.data, "tick", None)
                if payload:
                    try:
                        if hasattr(self, "_orderbook_widget") and self._orderbook_widget:
                            self._orderbook_widget.update_from_orderbook(payload)
                    except Exception:
                        pass
                    try:
                        if hasattr(self, "_funding_widget") and self._funding_widget:
                            fw = payload.get("funding") if isinstance(payload, dict) else None
                            if fw:
                                self._funding_widget.update_from_funding({"funding": fw})
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                # trigger a render to pick up updated market_context + widget state
                self._render()
            except Exception:
                pass
        except Exception:
            return

    async def _bg_fetch_whales(self) -> None:
        """Fetch whale trades in a background thread and update widgets."""
        try:
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
            self._update_whales_widget(result)
            try:
                if isinstance(result.data, dict):
                    setattr(self.app, "_whales_snapshot", result.data)
            except Exception:
                pass
            try:
                self._render()
            except Exception:
                pass
        except Exception:
            return

    async def _bg_fetch_funding(self) -> None:
        """Fetch funding data in a background thread and update widgets."""
        try:
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
            self._update_funding_widget(result)
            try:
                self._render()
            except Exception:
                pass
        except Exception:
            return

    def _update_whales_widget(self, result: Optional[FeedResult]) -> None:
        try:
            if hasattr(self, "_whales_widget") and self._whales_widget:
                if result and isinstance(result.data, dict):
                    self._whales_widget.update_from_whales(result.data)
        except Exception:
            pass

    def _update_funding_widget(self, result: Optional[FeedResult]) -> None:
        try:
            if hasattr(self, "_funding_widget") and self._funding_widget:
                if result and isinstance(result.data, dict):
                    self._funding_widget.update_from_funding(result.data)
        except Exception:
            pass

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

    def _measure_loop_lag(self) -> None:
        """Measure event-loop lag and expose it to the render path for diagnostics."""
        try:
            now = time.monotonic()
            if self._last_loop_tick is None:
                self._last_loop_tick = now
                return
            elapsed = now - self._last_loop_tick
            # ideal interval is 1.0s (set_interval); lag is extra time beyond that
            lag = max(0.0, elapsed - 1.0)
            self._loop_lag_ms = int(lag * 1000)
            self._last_loop_tick = now
        except Exception:
            self._loop_lag_ms = 0

    def _render(self) -> None:
        now_ms = int(time.time() * 1000)
        result = self._liq_result
        snapshot = (
            result.data
            if isinstance(result and result.data, LiquidationSnapshot)
            else None
        )
        status_label = _status_label(result)
        status_line = _status_line(result, now_ms)
        # append event-loop lag diagnostic to help debug input/key latency
        try:
            if getattr(self, "_loop_lag_ms", 0):
                status_line = f"{status_line} | loop_lag={self._loop_lag_ms}ms"
        except Exception:
            pass
        self.set_status(status_line)

        lines: List[str] = []
        lines.append(f"Liquidations Radar [{status_label}]")

        if (
            result
            and result.error
            and _as_status(result.status) in {FeedStatus.ERROR, FeedStatus.DISCONNECTED}
            and not snapshot
        ):
            lines.append(f"ERROR: {result.error}")
            lines.append(
                "Hint: verify API key + connectivity. Data will retry with backoff."
            )
            self.body.update("\n".join(lines))
            return

        if snapshot:
            lines.extend(
                _build_liquidation_lines(
                    snapshot,
                    self._market_result,
                    getattr(self.app, "selected_symbol", "BTC"),
                    self._positions_snapshot,
                )
            )
            updater = getattr(self.app, "set_top_symbols", None)
            if updater:
                updater(_collect_symbols(snapshot))
        else:
            lines.append("Waiting for liquidation data...")
        self.body.update("\n".join(lines))


def _render_top_symbols(
    snapshot: LiquidationSnapshot, selected_symbol: str
) -> tuple[List[str], List[str]]:
    lines: List[str] = ["Top symbols (15m)"]
    top = snapshot.top_symbols.get("15m") or snapshot.top_symbols.get("5m") or []
    max_val = max([float(row.get("notional") or 0.0) for row in top], default=1.0)
    symbols: List[str] = []
    for idx, row in enumerate(top[:8], start=1):
        symbol = str(row.get("symbol") or "?")
        marker = "*" if symbol.upper() == (selected_symbol or "").upper() else " "
        bar = heat_bar(float(row.get("notional") or 0.0), max_val, width=14)
        lines.append(
            f"{idx:>2}. {marker}{symbol:<6} {bar} ${float(row.get('notional') or 0.0):,.0f}"
        )
        symbols.append(symbol)
    if not top:
        lines.append("No symbol aggregates yet.")
    return lines, symbols


def _render_market_context(result: Optional[FeedResult]) -> List[str]:
    lines: List[str] = ["Microstructure Context (lite)"]
    context = result.data if isinstance(result and result.data, MarketContext) else None
    if context:
        lines.append(
            f"{context.symbol} last={_fmt_num(context.last_price)} bid={_fmt_num(context.best_bid)} "
            f"ask={_fmt_num(context.best_ask)} spread_bps={_fmt_num(context.spread_bps)}"
        )
        if context.funding_rate is not None or context.open_interest is not None:
            lines.append(
                f"funding={_fmt_num(context.funding_rate)} oi={_fmt_num(context.open_interest)}"
            )
        return lines
    if result and result.error and _as_status(result.status) in {FeedStatus.ERROR, FeedStatus.DISCONNECTED}:
        lines.append(f"ERROR: {result.error}")
        lines.append("Hint: market context uses price/orderbook endpoints.")
    else:
        lines.append("No market context yet.")
    return lines


def _render_heatmap(snapshot: LiquidationSnapshot) -> List[str]:
    lines: List[str] = ["Liquidation Heatmap (Top 15m)"]
    top = snapshot.top_symbols.get("15m") or []
    max_val = max([float(row.get("notional") or 0.0) for row in top], default=1.0)
    if not top:
        lines.append("No heatmap data yet.")
        return lines
    for row in top[:8]:
        symbol = str(row.get("symbol") or "?")
        bar = heat_bar(float(row.get("notional") or 0.0), max_val, width=18)
        lines.append(f"{symbol:<6} {bar}")
    return lines


def _render_liquidation_distance(positions: List[Dict[str, Any]]) -> List[str]:
    lines: List[str] = ["Liquidation Distance"]
    if not positions:
        lines.append("Positions feed not available yet.")
        return lines
    rows = []
    for pos in positions:
        symbol = _coerce_str(pos.get("symbol") or pos.get("coin") or pos.get("asset"))
        liq_price = _coerce_float(
            pos.get("liquidation_price")
            or pos.get("liq_price")
            or pos.get("liquidationPrice")
        )
        mark_price = _coerce_float(
            pos.get("mark_price") or pos.get("price") or pos.get("mark")
        )
        side = _coerce_str(pos.get("side") or pos.get("direction") or "")
        if not symbol or liq_price is None or mark_price is None or mark_price == 0:
            continue
        distance_pct = abs(liq_price - mark_price) / mark_price * 100.0
        rows.append((symbol, side or "?", distance_pct))
    if not rows:
        lines.append("No liquidation distance data available.")
        return lines
    max_val = max([row[2] for row in rows], default=1.0)
    for symbol, side, distance_pct in rows[:8]:
        bar = heat_bar(distance_pct, max_val, width=12)
        lines.append(f"{symbol:<6} {side:<5} {bar} {distance_pct:.2f}%")
    return lines


def _render_cascade_monitor(snapshot: LiquidationSnapshot) -> List[str]:
    cascade = snapshot.cascade
    lines = [
        "Cascade Monitor",
        f"Level: {cascade.level} | Score: {cascade.score:.2f}",
        f"Reason: {cascade.reason}",
    ]
    return lines


def _build_liquidation_lines(
    snapshot: LiquidationSnapshot,
    market_result: Optional[FeedResult],
    selected_symbol: str,
    positions_snapshot: Optional[Dict[str, Any]],
) -> List[str]:
    lines: List[str] = []
    lines.append("Rolling totals (1m/5m/15m)")
    for key in ("1m", "5m", "15m"):
        roll = snapshot.rollups.get(key)
        if not roll:
            continue
        lines.append(
            f"{key}: {roll.count} liqs | ${roll.notional:,.0f} | L/S {roll.long_count}/{roll.short_count}"
        )
    spark = sparkline(snapshot.series_notional, width=30)
    if spark:
        lines.append(f"Notional sparkline: {spark}")
    lines.append("")
    lines.extend(_render_cascade_monitor(snapshot))
    lines.append("")
    lines.append("Recent liquidations")
    for event in snapshot.events[:8]:
        lines.append(
            f"{_fmt_ts(event.ts_ms)} {event.symbol:<6} {event.side:<9} ${event.notional_usd or 0:,.0f}"
        )
    lines.append("")
    lines_top, _ = _render_top_symbols(snapshot, selected_symbol)
    lines.extend(lines_top)
    lines.append("")
    lines.extend(_render_heatmap(snapshot))
    lines.append("")
    positions = _extract_positions(positions_snapshot)
    lines.extend(_render_liquidation_distance(positions))
    lines.append("")
    lines.extend(_render_market_context(market_result))
    lines.append("")
    lines.extend(_render_capture_status(snapshot))
    lines.append("")
    lines.append(
        "Commands: view time | view heatmap | view table | select <symbol|#> | capture on|off"
    )
    return lines


def _render_capture_status(snapshot: LiquidationSnapshot) -> List[str]:
    capture = snapshot.capture
    status = "ON" if capture.enabled else "OFF"
    last_ts = _fmt_ts(capture.last_export_ts_ms) if capture.last_export_ts_ms else "n/a"
    size_mb = capture.total_bytes / (1024 * 1024) if capture.total_bytes else 0.0
    lines = [
        "Export / Capture Status",
        f"capture={status} | last_export={last_ts} | files={capture.file_count} | size={size_mb:.2f} MB",
    ]
    if capture.base_path:
        lines.append(f"path={capture.base_path}")
    lines.append("Backtests use local data only.")
    return lines


def _collect_symbols(snapshot: LiquidationSnapshot) -> List[str]:
    top = snapshot.top_symbols.get("15m") or snapshot.top_symbols.get("5m") or []
    return [str(row.get("symbol") or "?") for row in top]


def _load_positions_snapshot(app) -> Optional[Dict[str, Any]]:
    try:
        registry = DatasetRegistry(path=app.config.data_root / "_registry.json")
    except Exception:
        return None
    return load_latest_snapshot(registry, "feed=positions", "live")


def _extract_positions(snapshot: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(snapshot, dict):
        return []
    for key in ("positions", "data", "rows", "items"):
        value = snapshot.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    if isinstance(snapshot.get("snapshot"), dict):
        inner = snapshot["snapshot"]
        for key in ("positions", "data", "rows", "items"):
            value = inner.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    return []


def _status_label(result: Optional[FeedResult]) -> str:
    if result is None:
        return "LOADING"
    status = _as_status(result.status)
    if status == FeedStatus.OK:
        return "LIVE"
    if status == FeedStatus.EMPTY:
        return "NO DATA"
    if status in {FeedStatus.ERROR, FeedStatus.DISCONNECTED} and result.is_lkg:
        return "STALE"
    if status == FeedStatus.DISCONNECTED:
        return "DISCONNECTED"
    return "ERROR"


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
    status = _as_status(result.status)
    return f"Status: {status.value} | Last update: {updated_str}{stale}"


def _fmt_ts(ts_ms: Optional[int]) -> str:
    if not ts_ms:
        return "n/a"
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    return dt.strftime("%H:%M:%S")


def _fmt_num(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    if abs(value) >= 1000:
        return f"{value:,.2f}"
    return f"{value:.4f}"


def _coerce_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        text = str(value).strip()
    except Exception:
        return None
    return text or None
