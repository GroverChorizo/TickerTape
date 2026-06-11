"""Ops screen: data health, signal tape, and bot health.

The operational view of the Bot–TickerTape Interface Contract: what the
datadogs store looks like, what the bots are saying, and whether they are
alive. Reachable from every profile via the sidebar "Ops" entry or `:ops`.
"""

from __future__ import annotations

from textual.containers import Horizontal, Vertical
from textual.widgets import TabbedContent, TabPane

from tui.ui.screens.base import BaseScreen
from tui.widgets.bot_health_panel import BotHealthPanel
from tui.widgets.data_health_panel import DataHealthPanel, scan_health
from tui.widgets.signal_tape_panel import SignalTapePanel


class OpsScreen(BaseScreen):
    """Data Health / Signal Tape / Bot Health, refreshed from local files only."""

    def __init__(self) -> None:
        super().__init__(
            screen_id="ops",
            title="Ops",
            context="ops",
        )
        self.data_health_panel = DataHealthPanel()
        self.signal_tape_panel = SignalTapePanel()
        self.bot_health_panel = BotHealthPanel()
        self._tabs = TabbedContent(id="ops_tabs")
        self._body = Vertical(id="screen_body")
        self.body = self._body

    # ── layout ────────────────────────────────────────────────────────────────

    def compose(self):
        with Vertical(id="screen_root"):
            yield self.header
            yield self.status
            yield self.tab_carousel
            with Horizontal(id="content_row"):
                yield self.sidebar
                with self._body:
                    with self._tabs:
                        with TabPane("Data Health", id="ops_tab_data"):
                            yield self.data_health_panel
                        with TabPane("Signal Tape", id="ops_tab_signals"):
                            yield self.signal_tape_panel
                        with TabPane("Bot Health", id="ops_tab_bots"):
                            yield self.bot_health_panel
            yield self.tabbar
            yield self.command_bar

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        self.set_header("Ops | Data & Bots")
        self.set_status(
            "Data Health: datadogs store freshness.  Signal Tape: signals.jsonl.  "
            "Bot Health: state/<bot>.json heartbeats."
        )
        self.data_health_panel.show_scanning()
        self._refresh_local()
        self._start_health_scan()
        self.set_interval(2.0, self._refresh_local)
        self.set_interval(15.0, self._start_health_scan)

    def on_show(self) -> None:
        super().on_show()
        self._refresh_local()
        self._start_health_scan()

    # ── refresh ───────────────────────────────────────────────────────────────

    def _refresh_local(self) -> None:
        """Cheap file reads (jsonl tail + small state files) — main thread is fine."""
        self.signal_tape_panel.refresh_panel()
        self.bot_health_panel.refresh_panel()

    def _start_health_scan(self) -> None:
        """CSV validation reads megabytes — keep it off the UI thread."""
        self.run_worker(
            self._scan_and_render,
            group="ops_health_scan",
            exclusive=True,
            thread=True,
        )

    def _scan_and_render(self) -> None:
        rows = scan_health()
        self.app.call_from_thread(self.data_health_panel.show_rows, rows)
