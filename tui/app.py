"""TickerTape TUI application."""
from __future__ import annotations

import argparse
import asyncio
import logging
import shlex
import sys
from pathlib import Path
from typing import Dict, List

def ensure_src_on_path() -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    return repo_root
ensure_src_on_path()


def _coerce_log_extra(kwargs: dict) -> dict:
    extra = dict(kwargs.pop("extra", {}))
    extra.update(kwargs)
    return extra


def _log_system(self: logging.Logger, message: str = "", *args, **kwargs) -> None:
    extra = _coerce_log_extra(kwargs)
    self.info(message or "", *args, extra=extra)


def _log_call(self: logging.Logger, message: str = "", *args, **kwargs) -> None:
    extra = _coerce_log_extra(kwargs)
    self.info(message or "", *args, extra=extra)


def _adapter_system(self: logging.LoggerAdapter, message: str = "", *args, **kwargs) -> None:
    extra = _coerce_log_extra(kwargs)
    self.logger.info(message or "", *args, extra=extra)


def _adapter_call(self: logging.LoggerAdapter, message: str = "", *args, **kwargs) -> None:
    extra = _coerce_log_extra(kwargs)
    self.logger.info(message or "", *args, extra=extra)


logging.Logger.system = _log_system  # type: ignore[attr-defined]
logging.Logger.__call__ = _log_call  # type: ignore[assignment]
logging.LoggerAdapter.system = _adapter_system  # type: ignore[attr-defined]
logging.LoggerAdapter.__call__ = _adapter_call  # type: ignore[assignment]

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Input, Static

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from .backend.registry import get_registry
from .bootstrap import bootstrap_data
from .config import TuiConfig, config_needs_setup, ensure_data_root, load_config, save_config
from .diagnostics import collect_diagnostics
from .wizard import StartupWizard
from .roadmap import RoadmapScreen
from .state.alerts import AlertStream
from .state.datasets import load_datasets
from .state.profiles import get_profile
from .state.research import ResearchQueue
from .state.session import get_profile_state, load_session_state, save_session_state
from .widgets.alert_panel import AlertPanel
from .widgets.backtest_panel import BacktestPanel
from .widgets.event_stream import EventStream
from .widgets.market_data_panel import MarketDataPanel
from .widgets.funding_panel import FundingPanel
from .widgets.liquidations_panel import LiquidationsPanel
from .widgets.profile_selector import ProfileSelector, ProfileSelected
from .widgets.status_bar import StatusBar
from .widgets.whale_panel import WhalePanel
from .widgets.wallet_panel import WalletPanel, WalletDetailPanel, WalletSelected, WalletsDiscovered
from backend.network import NetworkClient
from tui.themes.palettes import Palette
from tui.themes.theme_manager import ThemeManager
from tui.feeds.hyperliquid import (
    EventStreamFeed,
    FundingRatesFeed,
    HyperliquidClient,
    LiquidationsFeed,
    WhaleTradesFeed,
)
from tui.feeds.market_data import MarketDataFeed
from .streaming import StreamSupervisor
from .widgets.panel_base import PanelBase


class TickerTapeApp(App):
    CSS_PATH = "tui.css"
    BINDINGS = [
        ("ctrl+p", "focus_command", "Focus command"),
        ("ctrl+1", "toggle_panel('liquidations')", "Toggle liquidations"),
        ("ctrl+2", "toggle_panel('funding')", "Toggle funding"),
        ("ctrl+3", "toggle_panel('whales')", "Toggle whales"),
        ("ctrl+4", "toggle_panel('event_stream')", "Toggle event stream"),
        ("ctrl+5", "toggle_panel('alerts')", "Toggle alerts"),
        ("ctrl+6", "toggle_panel('research')", "Toggle research"),
        ("c", "cycle_coin", "Cycle coin"),
        ("r", "refresh_panels", "Refresh panels"),
        ("p", "open_plan", "Open roadmap"),
    ]

    def __init__(self, config: TuiConfig) -> None:
        super().__init__()
        self.config = config
        self.registry = get_registry()
        self.session_state = load_session_state()
        if self.config.profile:
            self.session_state.active_profile = self.config.profile
        self.alert_stream = AlertStream()
        self.research_queue = ResearchQueue()
        self.streams = StreamSupervisor()
        self.client = NetworkClient()
        self.live_client = HyperliquidClient()
        self.liquidations_stats_feed = LiquidationsFeed(self.live_client, offline=self.config.mode == "offline_demo")
        self.market_data_feed = MarketDataFeed(
            self.live_client,
            registry=self.registry,
            offline=self.config.mode == "offline_demo",
        )
        self.funding_feed = FundingRatesFeed(client=self.client, registry=self.registry, coins=None, poll_interval=10.0, offline=self.config.mode == "offline_demo")
        self.whales_feed = WhaleTradesFeed(self.live_client, offline=self.config.mode == "offline_demo")
        self.events_feed = EventStreamFeed(self.live_client, offline=self.config.mode == "offline_demo")
        self.streams.register(self.liquidations_stats_feed)
        self.streams.register(self.market_data_feed)
        self.streams.register(self.funding_feed)
        self.streams.register(self.whales_feed)
        self.streams.register(self.events_feed)
        self._panels: Dict[str, Static] = {}
        self._last_snapshot_ts: int | None = None
        self._logger = logging.getLogger(__name__)
        self.theme_manager = ThemeManager(self.session_state)
        self._palette: Palette = self.theme_manager.current()

    def compose(self) -> ComposeResult:
        active_profile = self.session_state.active_profile
        profile = get_profile(active_profile)
        yield Static("TickerTape", id="title")
        with Horizontal(id="body"):
            with Vertical(id="left"):
                yield Static("Profiles", classes="section")
                yield ProfileSelector(active_profile)
                yield Static("Command shortcuts", classes="section")
                yield Static(
                    "ctrl+p command | /profile <name> | /backtest run | /backtest sweep",
                    classes="help",
                )
            with Vertical(id="center"):
                liquidations = LiquidationsPanel()
                positions = MarketDataPanel()
                funding = FundingPanel()
                whales = WhalePanel()
                events = EventStream()
                research = BacktestPanel(self.research_queue)
                self._panels = {
                    "liquidations": liquidations,
                    "positions": positions,
                    "funding": funding,
                    "whales": whales,
                    "event_stream": events,
                    "research": research,
                }
                self._apply_palette_to_panels(self._palette)
                order = get_profile_state(self.session_state, profile.name).panel_order
                for panel_id in order:
                    panel = self._panels.get(panel_id)
                    if panel is not None:
                        yield panel
            with Vertical(id="right"):
                alert_panel = AlertPanel(self.alert_stream)
                self._panels["alerts"] = alert_panel
                yield alert_panel
                wallet_panel = WalletPanel()
                self._panels["wallets"] = wallet_panel
                yield wallet_panel
                wallet_detail = WalletDetailPanel()
                self._panels["wallet_detail"] = wallet_detail
                yield wallet_detail
        with Vertical(id="footer"):
            yield Input(placeholder="Command palette: /profile, /backtest, /montecarlo, /walkforward", id="command")
            yield StatusBar(id="status")
            yield Footer()

    def on_mount(self) -> None:
        self.apply_palette(self._palette)
        self.alert_stream.start()
        self.set_interval(5, self.refresh_panels)
        self.set_interval(2, self.refresh_status)
        self.apply_profile(self.session_state.active_profile)
        if getattr(self, "_show_wizard", False):
            self.call_later(self._open_wizard)
        self.streams.start()

    def on_shutdown(self) -> None:
        self.streams.stop()
        try:
            self.client.close()
        except Exception:
            pass
        try:
            self.live_client.close()
        except Exception:
            pass

    def refresh_panels(self) -> None:
        liquidations = self._panels.get("liquidations")
        if isinstance(liquidations, LiquidationsPanel):
            self._safe_refresh(
                liquidations,
                "liquidations",
                lambda: liquidations.update_feed(self.liquidations_stats_feed.latest()),
            )
            self._last_snapshot_ts = self.liquidations_stats_feed.latest().updated_ts_ms
        positions = self._panels.get("positions")
        if isinstance(positions, MarketDataPanel):
            self._safe_refresh(positions, "positions", lambda: positions.update_feed(self.market_data_feed.latest()))
        funding = self._panels.get("funding")
        if isinstance(funding, FundingPanel):
            self._safe_refresh(funding, "funding", lambda: funding.update_feed(self.funding_feed.latest()))
        whales = self._panels.get("whales")
        if isinstance(whales, WhalePanel):
            self._safe_refresh(whales, "whales", lambda: whales.update_feed(self.whales_feed.latest()))
        events = self._panels.get("event_stream")
        if isinstance(events, EventStream):
            self._safe_refresh(events, "event_stream", lambda: events.update_feed(self.events_feed.latest()))
        alerts = self._panels.get("alerts")
        if isinstance(alerts, AlertPanel):
            self._safe_refresh(alerts, "alerts", alerts.refresh_panel)
        research = self._panels.get("research")
        if isinstance(research, BacktestPanel):
            self._safe_refresh(research, "research", research.refresh_panel)

    def _safe_refresh(self, panel: Static, name: str, fn) -> None:
        try:
            fn()
        except Exception as exc:
            self._logger.exception("Panel refresh failed: %s", name)
            if hasattr(panel, "update_text"):
                panel.update_text(f"Panel error. Press R to retry. ({type(exc).__name__})")
            else:
                panel.update(f"Panel error. Press R to retry. ({type(exc).__name__})")

    def refresh_status(self) -> None:
        try:
            status = self.query_one(StatusBar)
        except Exception:
            return
        datasets = load_datasets(self.registry)
        backend_ok = bool(datasets)
        status.update_status(
            profile=self.session_state.active_profile,
            backend_ok=backend_ok,
            active_jobs=len([j for j in self.research_queue.jobs if j.status in {"queued", "running"}]),
            last_snapshot_ts=self._last_snapshot_ts,
            alert_count=len(self.alert_stream.alerts),
            alert_connected=self.alert_stream.connected,
            feeds="local",
        )

    def apply_profile(self, profile_name: str) -> None:
        profile = get_profile(profile_name)
        for panel_id, panel in self._panels.items():
            if panel_id in profile.focus_panels:
                panel.remove_class("dim")
                if isinstance(panel, PanelBase):
                    panel.set_focus(True)
            else:
                panel.add_class("dim")
                if isinstance(panel, PanelBase):
                    panel.set_focus(False)
        self.theme_manager.set_active_profile(profile_name)
        self._palette = self.theme_manager.current()
        self.apply_palette(self._palette)
        self.session_state.active_profile = profile_name
        save_session_state(self.session_state)

    def on_profile_selected(self, message: ProfileSelected) -> None:
        self.apply_profile(message.profile_name)

    def on_wallets_discovered(self, message: WalletsDiscovered) -> None:
        panel = self._panels.get("wallets")
        if isinstance(panel, WalletPanel):
            panel.update_wallets(message.addresses, message.source)

    def on_wallet_selected(self, message: WalletSelected) -> None:
        panel = self._panels.get("wallet_detail")
        if isinstance(panel, WalletDetailPanel):
            panel.update_wallet(message.address, message.source)

    def action_focus_command(self) -> None:
        self.query_one("#command", Input).focus()

    def action_toggle_panel(self, panel_id: str) -> None:
        panel = self._panels.get(panel_id)
        if not panel:
            self.notify(f"Unknown panel {panel_id}", severity="warning")
            return
        panel.display = not panel.display
        profile_state = get_profile_state(self.session_state, self.session_state.active_profile)
        profile_state.collapsed[panel_id] = not panel.display
        save_session_state(self.session_state)

    def action_refresh_panels(self) -> None:
        self.refresh_panels()

    def action_cycle_coin(self) -> None:
        coin = self.market_data_feed.cycle_coin()
        self.notify(f"Selected coin: {coin}")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value.strip()
        event.input.value = ""
        if not command:
            return
        self.handle_command(command)

    def handle_command(self, command: str) -> None:
        tokens = shlex.split(command)
        if not tokens:
            return
        if tokens[0].startswith(":") or tokens[0].startswith("/"):
            tokens[0] = tokens[0][1:]
        cmd = tokens[0]
        args = tokens[1:]
        if cmd == "profile":
            if not args:
                self.notify("Usage: /profile <name>", severity="warning")
                return
            self.apply_profile(args[0])
            return
        if cmd in {"backtest", "montecarlo", "walkforward"}:
            self.handle_research_command(cmd, args)
            return
        if cmd == "panel" and args:
            if args[0] == "toggle" and len(args) > 1:
                self.action_toggle_panel(args[1])
                return
        if cmd == "diag":
            self._show_diagnostics()
            return
        if cmd == "ingest":
            self._run_ingest_once()
            return
        if cmd == "plan":
            self._open_roadmap()
            return
        if cmd == "setup":
            self._open_wizard()
            return
        if cmd == "theme":
            if not args or args[0] == "list":
                themes = ", ".join(self.theme_manager.available())
                self.notify(f"Available themes: {themes}")
                return
            if args[0] == "set" and len(args) > 1:
                self.theme_manager.set_active_profile(self.session_state.active_profile)
                self.theme_manager.apply(self, args[1])
                self.notify(f"Theme set to {self.theme_manager.current_id()}")
                return
            self.notify("Usage: /theme list | /theme set <name>", severity="warning")
            return
        if cmd == "coin":
            if not args:
                self.notify("Usage: /coin <symbol>", severity="warning")
                return
            self.market_data_feed.set_selected_coin(args[0])
            self.notify(f"Selected coin set to {self.market_data_feed.selected_coin}")
            return
        self.notify("Unknown command", severity="warning")

    def _show_diagnostics(self) -> None:
        data = collect_diagnostics(self.config, self.registry)
        lines = [f"{k}: {v}" for k, v in data.items()]
        self.console.print("\n".join(lines))
        self.notify("Diagnostics printed to console.")

    def _run_ingest_once(self) -> None:
        self.notify("Running ingestion once...")
        asyncio.create_task(asyncio.to_thread(bootstrap_data, self.config))

    def _open_wizard(self) -> None:
        wizard = StartupWizard(self.config.config_path)
        self.push_screen(wizard)

    def action_open_plan(self) -> None:
        self._open_roadmap()

    def _open_roadmap(self) -> None:
        self.push_screen(RoadmapScreen())

    def apply_palette(self, palette: Palette) -> None:
        self._palette = palette
        self.styles.background = palette.bg.primary
        self.styles.color = palette.text.primary
        try:
            title = self.query_one("#title")
            title.styles.background = palette.bg.panel
            title.styles.color = palette.accent.cyan
        except Exception:
            pass
        self._apply_palette_to_panels(palette)

    def _apply_palette_to_panels(self, palette: Palette) -> None:
        for panel in self._panels.values():
            if isinstance(panel, PanelBase):
                panel.set_palette(palette)

    def handle_research_command(self, job_type: str, args: List[str]) -> None:
        if not args:
            self.notify("Usage: /backtest run|sweep --strategy PATH --dataset NAME --timeframe TF", severity="warning")
            return
        sub = args[0]
        rest = args[1:]
        parsed = self._parse_args(rest)
        strategy = parsed.get("strategy")
        datasets = parsed.get("dataset", "").split(",") if parsed.get("dataset") else []
        timeframes = parsed.get("timeframe", "").split(",") if parsed.get("timeframe") else []
        seed = int(parsed["seed"]) if parsed.get("seed") else None
        if not strategy:
            self.notify("Missing --strategy PATH", severity="warning")
            return
        if sub == "run":
            params = {k.replace("param_", ""): v for k, v in parsed.items() if k.startswith("param_")}
            job = self.research_queue.add_job(
                job_type=job_type,
                strategy_path=strategy,
                datasets=datasets,
                timeframes=timeframes,
                parameters=params,
                seed=seed,
            )
            asyncio.create_task(asyncio.to_thread(self.research_queue.run_if_configured, job))
            self.notify(f"Queued {job_type} job {job.job_id}")
            return
        if sub == "sweep":
            grid: Dict[str, List[str]] = {}
            for key, value in parsed.items():
                if key.startswith("grid_"):
                    grid[key.replace("grid_", "")] = [v.strip() for v in value.split(",") if v.strip()]
            if not grid:
                self.notify("Sweep requires --grid param=value1,value2", severity="warning")
                return
            jobs = self.research_queue.add_sweep(
                job_type=job_type,
                strategy_path=strategy,
                datasets=datasets,
                timeframes=timeframes,
                parameter_grid=grid,
                seed=seed,
            )
            for job in jobs:
                asyncio.create_task(asyncio.to_thread(self.research_queue.run_if_configured, job))
            self.notify(f"Queued {len(jobs)} sweep jobs")
            return
        self.notify("Unknown research subcommand", severity="warning")

    @staticmethod
    def _parse_args(args: List[str]) -> Dict[str, str]:
        parsed: Dict[str, str] = {}
        it = iter(args)
        for token in it:
            if token.startswith("--"):
                key = token[2:]
                try:
                    value = next(it)
                except StopIteration:
                    value = ""
                if key == "param":
                    if "=" in value:
                        param_key, param_value = value.split("=", 1)
                        parsed[f"param_{param_key}"] = param_value
                elif key == "grid":
                    if "=" in value:
                        grid_key, grid_value = value.split("=", 1)
                        parsed[f"grid_{grid_key}"] = grid_value
                else:
                    parsed[key] = value
        return parsed


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TickerTape TUI")
    parser.add_argument("--setup", action="store_true", help="Run setup wizard")
    parser.add_argument("--profile", help="Start in profile")
    parser.add_argument("--data-root", help="Override data root")
    parser.add_argument("--offline", action="store_true", help="Force offline mode")
    return parser.parse_args(argv)


def run() -> None:
    args = _parse_args(sys.argv[1:])
    overrides = {}
    if args.profile:
        overrides["profile"] = args.profile
    if args.data_root:
        overrides["data_root"] = args.data_root
    if args.offline:
        overrides["mode"] = "offline_demo"
    config = load_config(overrides)
    ensure_data_root(config)
    if args.profile:
        config.profile = args.profile
        save_config(config)
    if args.data_root:
        save_config(config)
    try:
        from backend import storage as storage_module

        storage_module.BASE_PARQUET_ROOT = config.data_root
        storage_module.REGISTRY_PATH = config.data_root / "_registry.json"
    except Exception:
        pass
    app = TickerTapeApp(config)
    app._show_wizard = args.setup or config_needs_setup(config)
    app.run()


if __name__ == "__main__":
    run()
