"""Command Center — a Renaissance-style quant overview built on keyless data.

Four panels over the keyless Hyperliquid info API (no key required):
  • Regime        — trend + volatility-regime for the selected coin
  • Correlation   — cross-asset return-correlation matrix of the majors
  • Funding/Flow  — funding-rate extremes and open-interest leaders
  • Signal Health — live feed/stream freshness

All number-crunching lives in ``tui.analytics`` (pure, unit-tested); this
screen only fetches data on a worker thread and renders it. With no data
(offline) each panel shows an honest placeholder rather than fabricated values.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from rich.table import Table
from rich.text import Text
from textual import work
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, TabbedContent, TabPane

from tui import analytics
from tui.ui.screens.base import BaseScreen

MAJORS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE"]


def _closes_from_candles(raw: Any) -> List[float]:
    """Extract close prices from an HL candleSnapshot payload."""
    if isinstance(raw, dict):
        raw = raw.get("candles") or raw.get("data") or []
    out: List[float] = []
    if isinstance(raw, list):
        for c in raw:
            if isinstance(c, dict):
                v = c.get("c", c.get("close"))
                try:
                    out.append(float(v))
                except (TypeError, ValueError):
                    continue
    return out


class CommandCenterScreen(BaseScreen):
    """Keyless quant overview: regime, correlation, funding/OI flow, signal health."""

    def __init__(self) -> None:
        super().__init__(
            screen_id="command_center",
            title="Command Center",
            context="command_center",
        )
        self._regime = Static("Loading…", id="cc_regime")
        self._corr = Static("Loading…", id="cc_corr")
        self._flow = Static("Loading…", id="cc_flow")
        self._health = Static("Loading…", id="cc_health")
        self._tabs = TabbedContent(id="cc_tabs")
        self._body = Vertical(id="screen_body")
        self.body = self._body

    # ── layout ──────────────────────────────────────────────────────────────
    def compose(self):
        with Vertical(id="screen_root"):
            yield self.header
            yield self.status
            yield self.tab_carousel
            with Horizontal(id="content_row"):
                yield self.sidebar
                with self._body:
                    with self._tabs:
                        with TabPane("Regime", id="cc_tab_regime"):
                            yield self._regime
                        with TabPane("Correlation", id="cc_tab_corr"):
                            yield self._corr
                        with TabPane("Funding / Flow", id="cc_tab_flow"):
                            yield self._flow
                        with TabPane("Signal Health", id="cc_tab_health"):
                            yield self._health
            yield self.tabbar
            yield self.command_bar

    # ── lifecycle ───────────────────────────────────────────────────────────
    def on_mount(self) -> None:
        self.set_header("Command Center")
        self.set_status(
            "Keyless quant overview · regime · cross-asset correlation · "
            "funding/OI flow · signal health"
        )
        self._refresh()
        self.set_interval(15.0, self._refresh)

    def on_show(self) -> None:
        super().on_show()
        self._refresh()

    # ── data ────────────────────────────────────────────────────────────────
    def _is_offline(self) -> bool:
        cfg = getattr(self.app, "config", None)
        return bool(getattr(cfg, "mode", None) == "offline_demo")

    def _refresh(self) -> None:
        if self._is_offline():
            note = "Offline demo mode — live keyless data disabled."
            for w in (self._regime, self._corr, self._flow, self._health):
                w.update(note)
            return
        self._load_data()

    @work(thread=True, exclusive=True)
    def _load_data(self) -> None:
        client = getattr(getattr(self, "app", None), "provider", None)
        client = getattr(client, "_client", None)
        snapshot: List[Dict[str, Any]] = []
        closes: Dict[str, List[float]] = {}
        if client is not None:
            try:
                raw = client.get_json("ticks_latest")
                if isinstance(raw, list):
                    snapshot = [r for r in raw if isinstance(r, dict)]
            except Exception:
                snapshot = []
            for sym in MAJORS:
                try:
                    c = client.get_json(
                        "candles", symbol=sym, params={"interval": "1h", "limit": 48}
                    )
                    series = _closes_from_candles(c)
                    if len(series) >= 3:
                        closes[sym] = series
                except Exception:
                    continue
        selected = str(getattr(self.app, "selected_symbol", "BTC") or "BTC").upper()
        try:
            health = self.app.stream_manager.health()
        except Exception:
            health = {}
        app = getattr(self, "app", None)
        if app is not None:
            app.call_from_thread(self._render, snapshot, closes, selected, health)

    # ── render (pure given inputs → testable without network/threads) ─────────
    def _render(
        self,
        snapshot: Sequence[Dict[str, Any]],
        closes: Dict[str, List[float]],
        selected: str,
        health: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._regime.update(self._render_regime(selected, closes, snapshot))
        self._corr.update(self._render_correlation(closes))
        self._flow.update(self._render_flow(snapshot))
        self._health.update(self._render_health(health or {}))

    def _render_regime(self, selected, closes, snapshot):
        series = closes.get(selected) or next(iter(closes.values()), [])
        sym = selected if closes.get(selected) else (
            next(iter(closes), selected)
        )
        if not series:
            return Text("No candle data yet.", style="dim")
        r = analytics.regime(series)
        trend_color = {"up": "green", "down": "red", "flat": "yellow"}.get(
            r["trend"], "white"
        )
        t = Table.grid(padding=(0, 2))
        t.add_column(justify="right", style="bold")
        t.add_column()
        t.add_row("Symbol", sym)
        t.add_row("Trend", Text(str(r["trend"]).upper(), style=trend_color))
        t.add_row("Volatility", f"{r['vol_state']}  (pct {r['vol_pct']:.0%})")
        t.add_row("Realized vol", f"{r['vol']:.4%}")
        t.add_row("Drift vs SMA", f"{r.get('drift', 0.0):+.2%}")
        return t

    def _render_correlation(self, closes):
        if len(closes) < 2:
            return Text("Need ≥2 symbols with candles for correlation.", style="dim")
        symbols, matrix = analytics.correlation_matrix(closes)
        table = Table(title="1h return correlation", show_lines=False, expand=False)
        table.add_column("")
        for s in symbols:
            table.add_column(s, justify="right")
        for i, a in enumerate(symbols):
            cells = [Text(a, style="bold")]
            for j, _ in enumerate(symbols):
                v = matrix[i][j]
                if v is None:
                    cells.append(Text("·", style="dim"))
                else:
                    style = "green" if v > 0.5 else "red" if v < -0.5 else "white"
                    cells.append(Text(f"{v:+.2f}", style=style))
            table.add_row(*cells)
        return table

    def _render_flow(self, snapshot):
        if not snapshot:
            return Text("No market snapshot yet.", style="dim")
        ext = analytics.funding_extremes(snapshot, n=5)
        oi = analytics.oi_leaders(snapshot, n=5)
        table = Table.grid(padding=(0, 3))
        table.add_column()
        table.add_column()
        table.add_column()

        def col(title, pairs, fmt):
            inner = Table(title=title, show_edge=False)
            inner.add_column("sym", style="bold")
            inner.add_column("val", justify="right")
            for sym, val in pairs:
                inner.add_row(sym, fmt(val))
            return inner

        table.add_row(
            col("Funding +", ext["most_positive"], lambda v: Text(f"{v:+.4%}", style="green")),
            col("Funding −", ext["most_negative"], lambda v: Text(f"{v:+.4%}", style="red")),
            col("Open interest", oi, lambda v: f"{v:,.0f}"),
        )
        return table

    def _render_health(self, health):
        if not health:
            return Text("No live streams (keyless core starts on launch).", style="dim")
        table = Table(title="Stream health", show_lines=False)
        table.add_column("stream", style="bold")
        table.add_column("status")
        for name, item in sorted(health.items()):
            status = getattr(item, "status", item)
            status_str = getattr(status, "value", str(status))
            color = (
                "green" if "LIVE" in status_str.upper()
                else "red" if "OFFLINE" in status_str.upper()
                else "yellow"
            )
            table.add_row(name, Text(status_str, style=color))
        return table
