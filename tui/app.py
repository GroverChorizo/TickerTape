"""TickerTape TUI application."""
from __future__ import annotations

import asyncio
import logging
import shlex
import sys
from pathlib import Path
from typing import Dict, List

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
from .state.alerts import AlertStream
from .state.datasets import load_datasets
from .state.profiles import get_profile
from .state.research import ResearchQueue
from .state.session import get_profile_state, load_session_state, save_session_state
from .widgets.alert_panel import AlertPanel
from .widgets.backtest_panel import BacktestPanel
from .widgets.event_stream import EventStream
from .widgets.funding_panel import FundingPanel
from .widgets.liquidations_panel import LiquidationsPanel
from .widgets.profile_selector import ProfileSelector, ProfileSelected
from .widgets.status_bar import StatusBar
from .widgets.whale_panel import WhalePanel
from .widgets.wallet_panel import WalletPanel, WalletDetailPanel, WalletSelected, WalletsDiscovered


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
        ("r", "refresh_panels", "Refresh panels"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.registry = get_registry()
        self.session_state = load_session_state()
        self.alert_stream = AlertStream()
        self.research_queue = ResearchQueue()
        self._panels: Dict[str, Static] = {}
        self._last_snapshot_ts: int | None = None
        self._logger = logging.getLogger(__name__)

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
                funding = FundingPanel()
                whales = WhalePanel()
                events = EventStream()
                research = BacktestPanel(self.research_queue)
                self._panels = {
                    "liquidations": liquidations,
                    "funding": funding,
                    "whales": whales,
                    "event_stream": events,
                    "research": research,
                }
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
        self.alert_stream.start()
        self.set_interval(5, self.refresh_panels)
        self.set_interval(2, self.refresh_status)
        self.apply_profile(self.session_state.active_profile)

    def refresh_panels(self) -> None:
        liquidations = self._panels.get("liquidations")
        if isinstance(liquidations, LiquidationsPanel):
            self._safe_refresh(
                liquidations,
                "liquidations",
                lambda: liquidations.refresh_snapshots(),
            )
            latest = max((s.get("computed_at_ts_ms") for s in liquidations.snapshots.values()), default=None)
            self._last_snapshot_ts = latest
        funding = self._panels.get("funding")
        if isinstance(funding, FundingPanel):
            self._safe_refresh(funding, "funding", funding.refresh_panel)
        whales = self._panels.get("whales")
        if isinstance(whales, WhalePanel):
            self._safe_refresh(whales, "whales", whales.refresh_panel)
        events = self._panels.get("event_stream")
        if isinstance(events, EventStream):
            self._safe_refresh(events, "event_stream", events.refresh_panel)
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
        status = self.query_one(StatusBar)
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
                panel.add_class("focus")
            else:
                panel.remove_class("focus")
                panel.add_class("dim")
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
        self.notify("Unknown command", severity="warning")

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


def run() -> None:
    app = TickerTapeApp()
    app.run()


if __name__ == "__main__":
    run()
