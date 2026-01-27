"""Liquidation Hunter profile screen."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
import time

from tui.ui.screens.base import BaseScreen
from tui.models.liquidations import LiquidationSnapshot
from tui.models.market import MarketContext
from tui.feeds.base import FeedResult
from tui.render.sparkline import sparkline, heat_bar


class LiquidationHunterScreen(BaseScreen):
    def __init__(self) -> None:
        super().__init__(screen_id="profile_liquidation", title="Liquidation Hunter", context="liquidation")
        self._next_liq_fetch = 0.0
        self._next_market_fetch = 0.0
        self._liq_result: Optional[FeedResult] = None
        self._market_result: Optional[FeedResult] = None

    def on_mount(self) -> None:
        self.set_header("Liquidation Hunter | LIVE")
        self.set_status("Waiting for data...")
        self.set_interval(1.0, self._tick)

    def _tick(self) -> None:
        now = time.monotonic()
        provider = getattr(self.app, "provider", None)
        store = getattr(self.app, "state_store", None)
        if provider is None or store is None:
            return

        if now >= self._next_liq_fetch:
            result = provider.get_liquidations()
            self._liq_result = result
            self._next_liq_fetch = now + provider.liquidation_next_delay(result.status)
            if isinstance(result.data, LiquidationSnapshot):
                store.update_snapshot("liquidation_hunter", "snapshot", result.data, ts_ms=result.updated_ts_ms)
                cache_snapshot = getattr(self.app, "cache_snapshot", None)
                if cache_snapshot:
                    cache_snapshot("liquidation_hunter", "snapshot", result.data)
            if result.error:
                store.set_error("liquidation_hunter", "snapshot", result.error)

        if now >= self._next_market_fetch:
            symbol = getattr(self.app, "selected_symbol", "BTC") or "BTC"
            result = provider.get_market_context(symbol)
            self._market_result = result
            self._next_market_fetch = now + provider.market_next_delay(result.status)

        self._render()

    def _render(self) -> None:
        now_ms = int(time.time() * 1000)
        result = self._liq_result
        snapshot = result.data if isinstance(result and result.data, LiquidationSnapshot) else None
        status_label = _status_label(result)
        status_line = _status_line(result, now_ms)
        self.set_status(status_line)

        lines: List[str] = []
        lines.append(f"Liquidations Radar [{status_label}]")

        if result and result.error and result.status in {"error", "disconnected"} and not snapshot:
            lines.append(f"ERROR: {result.error}")
            lines.append("Hint: verify API key + connectivity. Data will retry with backoff.")
            self.body.update("\n".join(lines))
            return

        if snapshot:
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
            lines.append(f"Cascade risk: {snapshot.cascade.level} ({snapshot.cascade.reason})")
            if result and result.error and result.is_lkg:
                lines.append(f"Last error: {result.error}")
                lines.append("Showing last known good data.")
            lines.append("")
            lines.append("Recent liquidations")
            for event in snapshot.events[:8]:
                lines.append(
                    f"{_fmt_ts(event.ts_ms)} {event.symbol:<6} {event.side:<9} ${event.notional_usd or 0:,.0f}"
                )
            lines.append("")
            lines_top, symbols = _render_top_symbols(snapshot, getattr(self.app, "selected_symbol", "BTC"))
            lines.extend(lines_top)
            updater = getattr(self.app, "set_top_symbols", None)
            if updater:
                updater(symbols)
            lines.append("")
            lines.extend(_render_market_context(self._market_result))
            lines.append("")
            lines.extend(_render_capture_status(snapshot))
            lines.append("")
            lines.append("Commands: view time | view heatmap | view table | select <symbol|#> | capture on|off")
        else:
            lines.append("Waiting for liquidation data...")
        self.body.update("\n".join(lines))


def _render_top_symbols(snapshot: LiquidationSnapshot, selected_symbol: str) -> tuple[List[str], List[str]]:
    lines: List[str] = ["Top symbols (15m)"]
    top = snapshot.top_symbols.get("15m") or snapshot.top_symbols.get("5m") or []
    max_val = max([float(row.get("notional") or 0.0) for row in top], default=1.0)
    symbols: List[str] = []
    for idx, row in enumerate(top[:8], start=1):
        symbol = str(row.get("symbol") or "?")
        marker = "*" if symbol.upper() == (selected_symbol or "").upper() else " "
        bar = heat_bar(float(row.get("notional") or 0.0), max_val, width=14)
        lines.append(f"{idx:>2}. {marker}{symbol:<6} {bar} ${float(row.get('notional') or 0.0):,.0f}")
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
    if result and result.error and result.status in {"error", "disconnected"}:
        lines.append(f"ERROR: {result.error}")
        lines.append("Hint: market context uses price/orderbook endpoints.")
    else:
        lines.append("No market context yet.")
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


def _status_label(result: Optional[FeedResult]) -> str:
    if result is None:
        return "LOADING"
    if result.status == "ok":
        return "LIVE"
    if result.status == "empty":
        return "NO DATA"
    if result.status in {"error", "disconnected"} and result.is_lkg:
        return "STALE"
    if result.status == "disconnected":
        return "DISCONNECTED"
    return "ERROR"


def _status_line(result: Optional[FeedResult], now_ms: int) -> str:
    if result is None:
        return "Status: loading | HTTP: pending"
    updated = result.updated_ts_ms
    if updated:
        updated_str = datetime.fromtimestamp(updated / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    else:
        updated_str = "unknown"
    stale = ""
    if result.is_lkg and updated:
        stale_s = int((now_ms - updated) / 1000)
        stale = f" | STALE +{stale_s}s"
    return f"Status: {result.status} | Last update: {updated_str}{stale}"


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
