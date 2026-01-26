"""Top symbols panel for liquidation heat slice."""
from __future__ import annotations

import time
from typing import List, Optional

from tui.render.palette import build_text, heading_line, last_updated_line, muted_line, panel_header
from tui.render.sparkline import heat_bar
from tui.feeds.base import FeedResult
from .panel_base import PanelBase


class LiquidationsTopPanel(PanelBase):
    def __init__(self) -> None:
        super().__init__(panel_id="liquidations_top", title="Top Symbols")
        self.feed_result = FeedResult(status="loading")
        self.selected_symbol: Optional[str] = None
        self._symbols_15m: List[str] = []

    def update_feed(self, result: FeedResult, *, selected_symbol: Optional[str] = None) -> None:
        self.feed_result = result
        if selected_symbol:
            self.selected_symbol = selected_symbol
        self.refresh_panel()

    def resolve_symbol(self, token: str) -> Optional[str]:
        token = token.strip()
        if not token:
            return None
        if token.isdigit():
            idx = int(token) - 1
            if 0 <= idx < len(self._symbols_15m):
                return self._symbols_15m[idx]
        return token.upper()

    def refresh_panel(self) -> None:
        status = self.feed_result.status
        if status == "loading":
            self._render_loading()
            return
        if status in {"error", "disconnected"} and not self.feed_result.data:
            self._render_error(self.feed_result.error or "Unknown error")
            return
        if status == "empty" and not self.feed_result.data:
            self._render_empty("No data yet.")
            return
        self._render_data()

    def _render_loading(self) -> None:
        self.set_status_class("loading")
        lines = [
            panel_header(self.title, "loading", self.palette),
            last_updated_line(self.feed_result.updated_ts_ms, self.palette),
            muted_line("Loading top symbols...", self.palette),
        ]
        self.update_text(build_text(lines))

    def _render_empty(self, reason: str) -> None:
        self.set_status_class("empty")
        lines = [
            panel_header(self.title, "empty", self.palette),
            last_updated_line(self.feed_result.updated_ts_ms, self.palette),
            muted_line(f"No data. {reason}", self.palette),
        ]
        self.update_text(build_text(lines))

    def _render_error(self, error: str) -> None:
        self.set_status_class("error")
        lines = [
            panel_header(self.title, "error", self.palette),
            last_updated_line(self.feed_result.updated_ts_ms, self.palette),
            (error, self.palette.text.primary),
            ("Hint: Check API key or endpoint availability.", self.palette.text.muted),
        ]
        self.update_text(build_text(lines))

    def _render_data(self) -> None:
        payload = self.feed_result.data or {}
        top = payload.get("top_symbols", {}) if isinstance(payload, dict) else {}
        top_15m = top.get("15m", []) if isinstance(top, dict) else []
        top_5m = top.get("5m", []) if isinstance(top, dict) else []

        self.set_status_class("disconnected" if self.feed_result.status == "disconnected" else "ok")
        status_value = "disconnected" if self.feed_result.status == "disconnected" else "ok"
        lines: List[tuple[str, str]] = []
        lines.append(panel_header(self.title, status_value, self.palette))
        lines.append(last_updated_line(self.feed_result.updated_ts_ms, self.palette))
        if self.feed_result.status == "disconnected" or self.feed_result.is_lkg:
            lines.append(muted_line(f"Showing last known data. Stale {_fmt_stale(self.feed_result.updated_ts_ms)}", self.palette))

        label_15m = "Top symbols (15m)"
        if not isinstance(top_15m, list) or not top_15m:
            top_15m = top.get("24h", []) if isinstance(top, dict) else []
            label_15m = "Top symbols (24h fallback)"
        lines.append(heading_line(label_15m, self.palette))
        lines.extend(self._render_top_list(top_15m, update_cache=True))
        lines.append(heading_line("Top symbols (5m)", self.palette))
        lines.extend(self._render_top_list(top_5m, update_cache=False))
        lines.append(muted_line("Select: /liqs select <symbol|#>", self.palette))
        self.update_text(build_text(lines))

    def _render_top_list(self, rows: List[dict], *, update_cache: bool) -> List[tuple[str, str]]:
        if not isinstance(rows, list) or not rows:
            return [muted_line("No data.", self.palette)]
        max_value = max((row.get("notional") or 0.0) for row in rows) or 1.0
        out: List[tuple[str, str]] = []
        symbols: List[str] = []
        for idx, row in enumerate(rows[:8], 1):
            symbol = str(row.get("symbol") or "?")
            symbols.append(symbol)
            bar = heat_bar(float(row.get("notional") or 0.0), max_value, width=10)
            marker = ">" if self.selected_symbol and symbol == self.selected_symbol else " "
            out.append((f"{marker}{idx}. {symbol:<6} {bar}", self.palette.text.primary))
        if update_cache:
            self._symbols_15m = symbols
        return out


def _fmt_stale(updated_ts_ms: Optional[int]) -> str:
    if not updated_ts_ms:
        return "unknown"
    delta = int(time.time() * 1000) - int(updated_ts_ms)
    if delta < 0:
        delta = 0
    return f"+{int(delta / 1000)}s"
