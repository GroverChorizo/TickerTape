"""Microstructure context panel for selected liquidation symbol."""

from __future__ import annotations

import time
from typing import Any, List, Optional

from tui.render.palette import (
    build_text,
    heading_line,
    last_updated_line,
    muted_line,
    panel_header,
)
from tui.feeds.base import FeedResult
from .panel_base import PanelBase


class LiquidationsContextPanel(PanelBase):
    def __init__(self) -> None:
        super().__init__(
            panel_id="liquidations_context", title="Microstructure Context"
        )
        self._selected_symbol: Optional[str] = None
        self._liq_result = FeedResult(status="loading")
        self._market_result = FeedResult(status="loading")
        self._funding_result = FeedResult(status="loading")

    def update_context(
        self,
        *,
        selected_symbol: Optional[str],
        liquidation_result: FeedResult,
        market_result: FeedResult,
        funding_result: FeedResult,
    ) -> None:
        self._selected_symbol = selected_symbol
        self._liq_result = liquidation_result
        self._market_result = market_result
        self._funding_result = funding_result
        self.refresh_panel()

    def refresh_panel(self) -> None:
        status = self._liq_result.status
        if status == "loading":
            self._render_loading()
            return
        if status in {"error", "disconnected"} and not self._liq_result.data:
            self._render_error(self._liq_result.error or "Unknown error")
            return
        self._render_data()

    def _render_loading(self) -> None:
        self.set_status_class("loading")
        lines = [
            panel_header(self.title, "loading", self.palette),
            last_updated_line(self._liq_result.updated_ts_ms, self.palette),
            muted_line("Loading microstructure context...", self.palette),
        ]
        self.update_text(build_text(lines))

    def _render_error(self, error: str) -> None:
        self.set_status_class("error")
        lines = [
            panel_header(self.title, "error", self.palette),
            last_updated_line(self._liq_result.updated_ts_ms, self.palette),
            (error, self.palette.text.primary),
            ("Hint: Check API key or endpoint availability.", self.palette.text.muted),
        ]
        self.update_text(build_text(lines))

    def _render_data(self) -> None:
        self.set_status_class(
            "disconnected" if self._liq_result.status == "disconnected" else "ok"
        )
        status_value = (
            "disconnected" if self._liq_result.status == "disconnected" else "ok"
        )
        lines: List[tuple[str, str]] = []
        lines.append(panel_header(self.title, status_value, self.palette))
        lines.append(last_updated_line(self._liq_result.updated_ts_ms, self.palette))
        if self._liq_result.status == "disconnected" or self._liq_result.is_lkg:
            lines.append(
                muted_line(
                    f"Showing last known data. Stale {_fmt_stale(self._liq_result.updated_ts_ms)}",
                    self.palette,
                )
            )

        symbol = (self._selected_symbol or "BTC").upper()
        lines.append((f"Selected symbol: {symbol}", self.palette.text.primary))

        lines.append(heading_line("Funding (latest)", self.palette))
        lines.extend(self._render_funding(symbol))

        lines.append(heading_line("Market (quick)", self.palette))
        lines.extend(self._render_market(symbol))

        lines.append(muted_line("Context uses existing feeds only.", self.palette))
        self.update_text(build_text(lines))

    def _render_funding(self, symbol: str) -> List[tuple[str, str]]:
        payload = (
            self._funding_result.data
            if isinstance(self._funding_result.data, dict)
            else {}
        )
        rows = payload.get("rows") if isinstance(payload, dict) else None
        if not isinstance(rows, list) or not rows:
            return [muted_line("No funding data available.", self.palette)]
        lines: List[tuple[str, str]] = []
        matches = [
            row for row in rows if str(row.get("symbol") or "").upper() == symbol
        ]
        if not matches:
            return [muted_line("No funding rows for symbol.", self.palette)]
        for row in matches[:3]:
            exchange = row.get("exchange") or "?"
            rate = _fmt_rate(row.get("rate"))
            annual = _fmt_pct(row.get("annualized_pct"))
            status = row.get("status") or "?"
            lines.append(
                (
                    f"{exchange:<10} rate={rate} annual={annual} status={status}",
                    self.palette.text.primary,
                )
            )
        return lines

    def _render_market(self, symbol: str) -> List[tuple[str, str]]:
        payload = (
            self._market_result.data
            if isinstance(self._market_result.data, dict)
            else {}
        )
        if not isinstance(payload, dict):
            return [muted_line("No market data available.", self.palette)]
        quick = payload.get("quick") if isinstance(payload, dict) else None
        top_coins = payload.get("top_coins") if isinstance(payload, dict) else None
        oi = _find_open_interest(top_coins, symbol)
        lines: List[tuple[str, str]] = []
        if isinstance(quick, dict):
            bid = _fmt_num(quick.get("best_bid"))
            ask = _fmt_num(quick.get("best_ask"))
            mid = _fmt_num(quick.get("mid"))
            spread = _fmt_num(quick.get("spread"))
            lines.append(
                (
                    f"Bid {bid} | Ask {ask} | Mid {mid} | Spread {spread}",
                    self.palette.text.primary,
                )
            )
        else:
            lines.append(muted_line("No quick price data.", self.palette))
        if oi is not None:
            lines.append((f"Open interest: {oi}", self.palette.text.primary))
        return lines


def _fmt_rate(value: Any) -> str:
    try:
        return f"{float(value):+.6f}"
    except (TypeError, ValueError):
        return "n/a"


def _fmt_pct(value: Any) -> str:
    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "n/a"


def _fmt_num(value: Any) -> str:
    try:
        return f"{float(value):,.4f}"
    except (TypeError, ValueError):
        return "n/a"


def _find_open_interest(top_coins: Any, symbol: str) -> Optional[str]:
    if not isinstance(top_coins, list):
        return None
    for entry in top_coins:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("symbol") or "").upper() == symbol:
            oi = entry.get("open_interest")
            try:
                return f"{float(oi):,.2f}"
            except (TypeError, ValueError):
                return None
    return None


def _fmt_stale(updated_ts_ms: Optional[int]) -> str:
    if not updated_ts_ms:
        return "unknown"
    delta = int(time.time() * 1000) - int(updated_ts_ms)
    if delta < 0:
        delta = 0
    return f"+{int(delta / 1000)}s"
