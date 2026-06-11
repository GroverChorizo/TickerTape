"""TickerTape multi-screen, command-driven TUI."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
import time
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from textual.app import App
from textual import events
from textual.widgets import Input


def ensure_src_on_path() -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    return repo_root


ROOT = ensure_src_on_path()

from config.secrets import check_permissions, open_in_editor
from backend.secrets import (
    ensure_secrets_file as ensure_env_secrets_file,
    resolve_secrets_file_path,
    legacy_secrets_file_path,
    canonical_secrets_file_path,
)
from tui.core import cache as cache_store
from tui.core.cache import load_cache, save_cache
from tui.core.commands import CommandRegistry
from tui.core.router import Route, parse_route
from tui.core.state import StateStore
from tui.providers.hyperliquid import HyperliquidProvider
from tui.streaming import LiveStreamManager
from tui.state.profiles import get_profile, list_profiles
from tui.themes.theme_manager import ThemeManager
from tui.config import (
    TuiConfig,
    config_needs_setup,
    ensure_data_root,
    load_config,
    save_config,
    update_funding_exchanges,
)
from tui.state.session import load_session_state, save_session_state, get_profile_state
from tui.state.alerts import AlertStore, AlertStream
from tickertape.core.alerts import AlertEvent, AlertSeverity
from tui.ui.screens.home import HomeScreen
from tui.ui.screens.command_palette import CommandPaletteScreen
from tui.ui.screens.profile_day_trader import DayTraderScreen
from tui.ui.screens.profile_funding_arbitrage import FundingArbitrageScreen
from tui.ui.screens.profile_liquidation import LiquidationHunterScreen
from tui.ui.screens.profile_placeholder import PlaceholderProfileScreen
from tui.ui.screens.profile_whale_watcher import WhaleWatcherScreen
from tui.ui.screens.ops import OpsScreen
from tui.ui.screens.research import ResearchScreen
from tui.ui.screens.settings import SettingsScreen
from tui.ui.screens.validation import ValidationScreen
from tui.ui.screens.views import (
    LiquidationHeatmapView,
    LiquidationTableView,
    LiquidationTimeSeriesView,
)
from tui.ui.custom_dashboard import (
    apply_custom_dashboard,
    create_dashboard_from_state,
    load_custom_dashboards,
    save_custom_dashboard,
)
from backend.storage import DatasetRegistry
from backend.query_helpers import load_latest_snapshot
from tui.state.datasets import latest_timeframe, load_datasets
from tui.validation import extract_rows, run_validation
from commands.backtest import backtest_run_command
from commands.diagnose import diagnose_command
from commands.jobs import jobs_command
from backtesting.monte_carlo import resample_paths
from backtesting.job import DEFAULT_ROOT as JOB_ROOT, read_result


class TickerTapeApp(App):
    CSS_PATH = "tui.css"
    BINDINGS = [
        ("ctrl+p", "focus_command", "Focus command"),
        ("ctrl+h", "go_home", "Home"),
        ("ctrl+comma", "open_settings", "Settings"),
        ("ctrl+k", "open_palette", "Command palette"),
        ("/", "open_palette", "Command palette"),
    ]

    def __init__(self, config: TuiConfig) -> None:
        super().__init__()
        self.config = config
        self.secrets_notice: Optional[str] = None
        self.state_store = StateStore()
        self.command_registry = CommandRegistry()
        self.session_state = load_session_state()
        self.theme_manager = ThemeManager(self.session_state)
        self.theme_tokens: dict[str, str] = {}
        if cache_store.CACHE_PATH == cache_store.DEFAULT_CACHE_PATH:
            cache_store.CACHE_PATH = self.config.data_root / "ui_cache.json"
        self._cache = load_cache()
        self._cache.setdefault("preferences", {"refresh_interval_s": 1.0})
        self._errors: List[str] = []
        self.sidebar_hidden = bool(self._cache.get("sidebar_hidden", False))
        self._tt_screen_stack: List[str] = []
        self._screen_titles: dict[str, str] = {}
        self._screen_routes: dict[str, str] = {}
        self._command_history: List[str] = []
        self._history_index: int = 0
        self._top_symbols: List[str] = []
        self.selected_symbol = self._load_selected_symbol()
        self.alert_store = AlertStore()
        self._alert_last_ts: dict[str, int] = {}
        self.alert_stream = AlertStream(
            store=self.alert_store,
            on_alert=self._on_stream_alert,
        )
        registry_path = self.config.data_root / "_registry.json"
        self.provider = HyperliquidProvider(
            registry=DatasetRegistry(path=registry_path),
            offline=self.config.mode == "offline_demo",
        )
        self.stream_manager = LiveStreamManager(self.provider)
        self._status_last_messages_total = 0
        self._status_last_measure_ts_ms: Optional[int] = None
        self._custom_dashboards = load_custom_dashboards()
        if self.config.profile in self._custom_dashboards:
            apply_custom_dashboard(
                self.session_state,
                self.config.profile,
                self._custom_dashboards[self.config.profile],
            )
        self._register_commands()
        self._load_cached_snapshots()
        self._open_screen_order = list(self._cache.get("open_screens_order", []))
        self._pending_mc_result: Optional[tuple] = None

    def on_mount(self) -> None:
        self.apply_palette(self.theme_manager.current())
        self._push_screen(HomeScreen(), route="home")
        self.alert_stream.start()
        if self.config.mode != "offline_demo":
            try:
                self.stream_manager.start()
            except Exception as exc:
                self._record_error(f"stream_manager start failed: {exc}")
        self._warn_legacy_secrets_path()
        if self.secrets_notice:
            self.notify(self.secrets_notice, severity="information")
        if getattr(self, "_show_wizard", False):
            self.notify(
                "Setup required. Run with --setup to configure.", severity="warning"
            )

    def on_shutdown(self) -> None:
        try:
            self.stream_manager.stop()
        except Exception:
            pass
        try:
            self.provider.close()
        except Exception:
            pass
        save_cache(self._cache)

    def is_alert_enabled(self, alert_type: str) -> bool:
        try:
            return bool(self.config.alerts.get(alert_type, False))
        except Exception:
            return False

    def emit_alert(
        self,
        *,
        alert_type: str,
        severity: AlertSeverity,
        source_feed: str,
        payload: dict,
        key: str | None = None,
        min_interval_ms: int = 30000,
    ) -> bool:
        now_ms = int(time.time() * 1000)
        throttle_key = f"{alert_type}:{key or source_feed}"
        last = self._alert_last_ts.get(throttle_key)
        if last is not None and (now_ms - last) < min_interval_ms:
            return False
        event = AlertEvent(
            alert_type=alert_type,
            severity=severity,
            source_feed=source_feed,
            timestamp_ms=now_ms,
            payload=payload or {},
        )
        self.alert_store.add(event)
        if not self.alert_store.muted:
            self._notify_alert(event)
        self._alert_last_ts[throttle_key] = now_ms
        return True

    def _notify_alert(self, alert: AlertEvent) -> None:
        if alert.severity == AlertSeverity.CRITICAL:
            level = "error"
        elif alert.severity == AlertSeverity.WARNING:
            level = "warning"
        else:
            level = "information"
        try:
            self.notify(
                f"{alert.alert_type}: {alert.payload.get('message', '')}".strip(),
                severity=level,
            )
        except Exception:
            pass

    def _on_stream_alert(self, alert: AlertEvent) -> None:
        if self.alert_store.muted:
            return
        self._notify_alert(alert)

    def apply_palette(self, palette) -> None:
        self.styles.background = palette.bg.primary
        self.styles.color = palette.text.primary
        self.theme_tokens = palette.to_tokens()
        self._apply_palette_to_screen(palette)

    def _apply_palette_to_screen(self, palette) -> None:
        self._apply_theme_class(palette.theme_id)
        try:
            header = self.screen.query_one("#screen_header")
            header.styles.background = palette.bg.panel
            header.styles.color = palette.accent.purple
        except Exception:
            pass
        try:
            status = self.screen.query_one("#status_line")
            status.styles.color = palette.text.muted
        except Exception:
            pass
        try:
            health = self.screen.query_one("#health_line")
            health.styles.color = palette.text.muted
        except Exception:
            pass
        try:
            breadcrumb = self.screen.query_one("#breadcrumb_line")
            breadcrumb.styles.color = palette.text.muted
        except Exception:
            pass
        try:
            diagnostics_button = self.screen.query_one("#status_diagnostics")
            diagnostics_button.styles.background = palette.bg.panel
            diagnostics_button.styles.color = palette.text.primary
        except Exception:
            pass
        try:
            alerts_button = self.screen.query_one("#status_alerts")
            alerts_button.styles.background = palette.bg.panel
            alerts_button.styles.color = palette.text.primary
        except Exception:
            pass
        try:
            carousel = self.screen.query_one("#tab_carousel")
            carousel.styles.background = palette.bg.panel
            carousel.styles.color = palette.text.primary
            if hasattr(carousel, "set_palette"):
                carousel.set_palette(palette)
        except Exception:
            pass
        try:
            body = self.screen.query_one("#screen_body")
            body.styles.background = palette.bg.primary
            body.styles.color = palette.text.primary
        except Exception:
            pass
        try:
            sidebar = self.screen.query_one("#sidebar")
            sidebar.styles.background = palette.bg.panel
            sidebar.styles.color = palette.text.primary
            if hasattr(sidebar, "set_palette"):
                sidebar.set_palette(palette)
        except Exception:
            pass
        try:
            command = self.screen.query_one("#command")
            command.styles.background = palette.bg.panel
            command.styles.color = palette.text.primary
        except Exception:
            pass
        try:
            palette_input = self.screen.query_one("#palette_input")
            palette_input.styles.background = palette.bg.panel
            palette_input.styles.color = palette.text.primary
        except Exception:
            pass
        try:
            palette_suggestions = self.screen.query_one("#palette_suggestions")
            palette_suggestions.styles.color = palette.text.primary
        except Exception:
            pass
        try:
            tabbar = self.screen.query_one("#tabbar")
            tabbar.styles.background = palette.bg.panel
            tabbar.styles.color = palette.text.primary
            if hasattr(tabbar, "set_palette"):
                tabbar.set_palette(palette)
        except Exception:
            pass
        try:
            cmd_status = self.screen.query_one("#command_status")
            cmd_status.styles.color = palette.text.muted
        except Exception:
            pass

    def _apply_theme_class(self, theme_id: str) -> None:
        try:
            screen = self.screen
        except Exception:
            return
        classes = list(getattr(screen, "classes", []))
        for name in classes:
            if name.startswith("theme-"):
                try:
                    screen.remove_class(name)
                except Exception:
                    pass
        try:
            screen.add_class(f"theme-{theme_id}")
        except Exception:
            pass

    def action_focus_command(self) -> None:
        try:
            self.screen.command_bar.input.focus()
        except Exception:
            pass

    def action_go_home(self) -> None:
        self._go_home()

    def action_open_settings(self) -> None:
        self._open_settings()

    def action_open_palette(self) -> None:
        context = getattr(self.screen, "command_context", "home")
        self.push_screen(CommandPaletteScreen(context=context))

    def dispatch_command(self, raw: str, *, context: str) -> None:
        text = raw.strip()
        if not text:
            return
        self._record_history(text)

        route = parse_route(text)
        if route.kind != "unknown":
            self._open_route(route)
            return

        tokens = shlex.split(text)
        if not tokens:
            return
        cmd = tokens[0].lstrip("/:").lower()
        args = tokens[1:]
        command = self.command_registry.match(cmd)
        if not command:
            self._set_command_message(
                "Unknown command. Type 'help' for available commands."
            )
            return
        message = command.handler(cmd, args)
        if message:
            self._set_command_message(message)

    def on_key(self, event: events.Key) -> None:
        focused = self.focused
        if not isinstance(focused, Input) or focused.id != "command":
            return
        if event.key == "up":
            self._history_prev(focused)
            event.stop()
        elif event.key == "down":
            self._history_next(focused)
            event.stop()
        elif event.key == "tab":
            self._autocomplete(focused)
            event.stop()

    def _record_history(self, text: str) -> None:
        if not text:
            return
        if not self._command_history or self._command_history[-1] != text:
            self._command_history.append(text)
        self._history_index = len(self._command_history)

    def _history_prev(self, input_widget: Input) -> None:
        if not self._command_history:
            return
        self._history_index = max(self._history_index - 1, 0)
        input_widget.value = self._command_history[self._history_index]

    def _history_next(self, input_widget: Input) -> None:
        if not self._command_history:
            return
        self._history_index = min(self._history_index + 1, len(self._command_history))
        if self._history_index >= len(self._command_history):
            input_widget.value = ""
        else:
            input_widget.value = self._command_history[self._history_index]

    def _autocomplete(self, input_widget: Input) -> None:
        text = input_widget.value.strip()
        suggestion = self._autocomplete_for(text)
        if suggestion:
            input_widget.value = suggestion

    def _autocomplete_for(self, text: str) -> Optional[str]:
        command_names = sorted(
            {cmd.name for cmd in self.command_registry._commands.values()}
        )
        profiles = [profile.name for profile in list_profiles()]
        views = ["time", "heatmap", "table"]
        route_candidates = [
            "home",
            "/",
            *[f"profile/{p}" for p in profiles],
            *[f"view/{v}" for v in views],
        ]
        if not text:
            return "help"
        if " " not in text:
            prefix = text.lower()
            for item in [*command_names, *route_candidates]:
                if item.startswith(prefix):
                    return item + (" " if item in command_names else "")
            return None
        parts = text.split()
        if len(parts) == 1:
            return text
        if parts[0] in {"profile", "view"}:
            choices = profiles if parts[0] == "profile" else views
            prefix = parts[-1].lower()
            for item in choices:
                if item.startswith(prefix):
                    return f"{parts[0]} {item}"
        return None

    def _set_command_message(self, message: str) -> None:
        try:
            self.screen.command_bar.set_message(message)
        except Exception:
            pass

    def get_status_snapshot(self) -> Dict[str, Any]:
        now_ms = int(time.time() * 1000)
        metrics = {}
        try:
            metrics = self.stream_manager.metrics()
        except Exception:
            metrics = {}
        ws_total = len(metrics)
        ws_live = sum(1 for item in metrics.values() if getattr(item, "active", False))
        message_total = sum(
            int(getattr(item, "messages_received", 0)) for item in metrics.values()
        )
        bandwidth_msg_s = 0.0
        if self._status_last_measure_ts_ms is not None:
            elapsed_s = max((now_ms - self._status_last_measure_ts_ms) / 1000.0, 0.001)
            delta = max(0, message_total - self._status_last_messages_total)
            bandwidth_msg_s = float(delta) / elapsed_s
        self._status_last_measure_ts_ms = now_ms
        self._status_last_messages_total = message_total

        stream_updates = {}
        try:
            stream_updates = self.stream_manager.stream_last_seen()
        except Exception:
            stream_updates = {}
        latest_stream_ts: Optional[int] = None
        for value in stream_updates.values():
            try:
                ts = int(value) if value is not None else None
            except Exception:
                ts = None
            if ts is None:
                continue
            latest_stream_ts = ts if latest_stream_ts is None else max(latest_stream_ts, ts)
        freshness_ms = (
            max(0, now_ms - latest_stream_ts) if latest_stream_ts is not None else None
        )

        client_metrics: Dict[str, Any] = {}
        try:
            getter = getattr(self.provider._client, "network_metrics", None)
            if callable(getter):
                result = getter()
                if isinstance(result, dict):
                    client_metrics = result
        except Exception:
            client_metrics = {}
        api_latency_ms = client_metrics.get("last_latency_ms")
        api_error = client_metrics.get("last_error")
        if self.config.mode == "offline_demo":
            connection = "offline"
            api_state = "offline"
        elif api_error:
            connection = "degraded"
            api_state = "error"
        elif ws_total == 0:
            connection = "unknown"
            api_state = "idle"
        elif ws_live == ws_total:
            connection = "live"
            api_state = "ok"
        elif ws_live == 0:
            connection = "offline"
            api_state = "degraded"
        else:
            connection = "degraded"
            api_state = "ok"

        return {
            "connection": connection,
            "api_state": api_state,
            "api_latency_ms": api_latency_ms,
            "ws_live": ws_live,
            "ws_total": ws_total,
            "freshness_ms": freshness_ms,
            "bandwidth_msg_s": bandwidth_msg_s,
            "alert_count": len(self.alert_store.alerts),
            "alert_muted": bool(self.alert_store.muted),
        }

    def _register_commands(self) -> None:
        self.command_registry.register(
            "help", "Show commands for this screen.", self._cmd_help
        )
        self.command_registry.register(
            "home", "Return to the home screen.", self._cmd_home, aliases=["/"]
        )
        self.command_registry.register(
            "quit", "Exit the application.", self._cmd_quit, aliases=["exit"]
        )
        self.command_registry.register(
            "reload", "Reload configuration.", self._cmd_reload
        )
        self.command_registry.register(
            "profile", "Open a profile screen.", self._cmd_profile
        )
        self.command_registry.register(
            "view", "Open a data view screen.", self._cmd_view
        )
        self.command_registry.register(
            "sidebar", "Toggle sidebar visibility.", self._cmd_sidebar
        )
        self.command_registry.register(
            "panel", "Open or focus a panel.", self._cmd_panel
        )
        self.command_registry.register(
            "fullscreen", "Toggle fullscreen mode.", self._cmd_fullscreen
        )
        self.command_registry.register(
            "alerts", "List or manage alerts.", self._cmd_alerts
        )
        self.command_registry.register(
            "tab", "Switch to a tab by name or index.", self._cmd_tab
        )
        self.command_registry.register(
            "grid", "Toggle grid layout density.", self._cmd_grid
        )
        self.command_registry.register(
            "diagnostics", "Run connectivity diagnostics.", self._cmd_diagnostics
        )
        self.command_registry.register(
            "jobs", "List or inspect backtest jobs.", self._cmd_jobs
        )
        self.command_registry.register(
            "select",
            "Select symbol from Top Symbols list (symbol or #).",
            self._cmd_select,
            contexts=["liquidation"],
            aliases=["symbol"],
        )
        self.command_registry.register(
            "capture",
            "Toggle liquidation capture on/off.",
            self._cmd_capture,
            contexts=["liquidation"],
        )
        self.command_registry.register(
            "secrets", "Open secrets file.", self._cmd_secrets
        )
        self.command_registry.register(
            "settings", "Open settings screen.", self._cmd_settings
        )
        self.command_registry.register("theme", "Switch UI theme.", self._cmd_theme)
        self.command_registry.register(
            "dashboard", "Manage custom dashboards.", self._cmd_dashboard
        )
        self.command_registry.register(
            "exchange",
            "Manage funding exchanges (list/add/remove).",
            self._cmd_exchange,
        )
        self.command_registry.register(
            "funding",
            "Funding actions (refresh).",
            self._cmd_funding,
        )
        self.command_registry.register(
            "validate", "Validate a dataset snapshot.", self._cmd_validate
        )
        self.command_registry.register(
            "watchlist",
            "Update watchlist symbols (comma-separated).",
            self._cmd_watchlist,
            contexts=["day_trader"],
        )
        self.command_registry.register("load", "Load a data stream.", self._cmd_load)
        self.command_registry.register(
            "refresh", "Refresh all data streams.", self._cmd_refresh
        )
        self.command_registry.register(
            "anomaly", "Run anomaly detection.", self._cmd_anomaly
        )
        self.command_registry.register("backtest", "Run backtest.", self._cmd_backtest)
        self.command_registry.register(
            "mc", "Run Monte Carlo stress test.", self._cmd_mc
        )
        self.command_registry.register(
            "bt_export", "Export backtest results.", self._cmd_bt_export
        )
        self.command_registry.register(
            "mc_export", "Export Monte Carlo results.", self._cmd_mc_export
        )
        self.command_registry.register(
            "export", "Export panel data locally.", self._cmd_export
        )
        self.command_registry.register(
            "log_export", "Export session logs.", self._cmd_log_export
        )
        self.command_registry.register(
            "inspect", "Inspect panel diagnostics.", self._cmd_inspect
        )
        self.command_registry.register(
            "metrics", "Show panel metrics.", self._cmd_metrics
        )
        self.command_registry.register(
            "errors", "Show recent errors.", self._cmd_errors
        )
        self.command_registry.register(
            "config", "Display current config.", self._cmd_config
        )
        self.command_registry.register(
            "whalefilter",
            "Filter whales by side and notional.",
            self._cmd_whalefilter,
            contexts=["whale_watcher"],
        )
        self.command_registry.register(
            "wallet",
            "Open wallet detail (address or #).",
            self._cmd_wallet,
            contexts=["whale_watcher"],
        )
        self.command_registry.register(
            "research",
            "Open the Research & Backtesting screen.",
            self._cmd_research,
            aliases=["bt", "lab"],
        )
        self.command_registry.register(
            "ops",
            "Open the Ops screen (data health, signal tape, bot health).",
            self._cmd_ops,
        )

    def _cmd_help(self, _cmd: str, _args: List[str]) -> str:
        context = getattr(self.screen, "command_context", "home")
        lines = self.command_registry.help_for(context)
        if not lines:
            return "No commands registered."
        return "\n".join(lines)

    def palette_suggestions(self, query: str) -> List[str]:
        query = query.strip().lower()
        history = list(reversed(self._command_history))
        command_map = {c.name: c for c in self.command_registry._commands.values()}
        commands = [
            f"{name} - {command_map[name].description}"
            for name in sorted(command_map.keys())
        ]
        profiles = [profile.name for profile in list_profiles()]
        views = ["time", "heatmap", "table"]
        routes = [
            "home",
            "settings",
            *[f"profile/{p}" for p in profiles],
            *[f"view/{v}" for v in views],
        ]
        items = history + commands + routes
        if not query:
            return items[:15]
        return [item for item in items if query in item.lower()][:15]

    def _cmd_home(self, _cmd: str, _args: List[str]) -> Optional[str]:
        self._go_home()
        return None

    def _cmd_quit(self, _cmd: str, _args: List[str]) -> Optional[str]:
        self.exit()
        return "Exiting..."

    def _cmd_reload(self, _cmd: str, _args: List[str]) -> str:
        try:
            self.config = load_config({"config_path": str(self.config.config_path)})
            ensure_data_root(self.config)
            registry_path = self.config.data_root / "_registry.json"
            self.provider = HyperliquidProvider(
                registry=DatasetRegistry(path=registry_path),
                offline=self.config.mode == "offline_demo",
            )
            return "Config reloaded."
        except Exception as exc:
            self._record_error(f"reload failed: {exc}")
            return f"Reload failed: {exc}"

    def _cmd_profile(self, _cmd: str, args: List[str]) -> str:
        if not args:
            return "Usage: profile <name>"
        name = args[0]
        self._open_profile(name)
        return ""

    def _cmd_view(self, _cmd: str, args: List[str]) -> str:
        if not args:
            return "Usage: view <time|heatmap|table>"
        self._open_view(args[0])
        return ""

    def _cmd_sidebar(self, _cmd: str, _args: List[str]) -> str:
        hidden = self._toggle_sidebar()
        return "Sidebar hidden." if hidden else "Sidebar shown."

    def _cmd_panel(self, _cmd: str, args: List[str]) -> str:
        if not args:
            return "Usage: panel <name>"
        target = args[0].strip().lower()
        if target in {"settings", "config"}:
            self._open_settings()
            return ""
        if target in {p.name for p in list_profiles()}:
            self._open_profile(target)
            return ""
        if target in {"time", "heatmap", "table"}:
            self._open_view(target)
            return ""
        return f"Panel not found: {target}"

    def _cmd_fullscreen(self, _cmd: str, _args: List[str]) -> str:
        screen = self.screen
        handler = getattr(screen, "action_toggle_fullscreen", None)
        if handler:
            handler()
            return "Toggled fullscreen."
        return "Fullscreen not available."

    def _cmd_tab(self, _cmd: str, args: List[str]) -> str:
        if not args:
            screens = self.get_open_screens()
            labels = [
                f"{idx + 1}:{entry['label']}" for idx, entry in enumerate(screens)
            ]
            return "Tabs: " + (", ".join(labels) if labels else "(none)")
        token = args[0]
        screens = self.get_open_screens()
        if token.isdigit():
            idx = int(token) - 1
            if 0 <= idx < len(screens):
                self.switch_to_screen_id(screens[idx]["key"])
                return ""
            return "Tab index out of range."
        for entry in screens:
            if entry["label"].lower().replace(" ", "_") == token.lower():
                self.switch_to_screen_id(entry["key"])
                return ""
        route = parse_route(token)
        if route.kind != "unknown":
            self._open_route(route)
            return ""
        return f"Tab not found: {token}"

    def _cmd_grid(self, _cmd: str, _args: List[str]) -> str:
        screen = self.screen
        handler = getattr(screen, "action_toggle_density", None)
        if handler:
            handler()
            return "Grid layout toggled."
        return "Grid layout not available."

    def _cmd_diagnostics(self, _cmd: str, _args: List[str]) -> str:
        try:
            return diagnose_command(self.provider)
        except Exception as exc:
            return f"Diagnostics failed: {exc}"

    def _cmd_jobs(self, _cmd: str, args: List[str]) -> str:
        if not args:
            self._open_research()
            return ""
        result = jobs_command("jobs", args)
        return result or ""

    def _cmd_research(self, _cmd: str, _args: List[str]) -> Optional[str]:
        self._open_research()
        return None

    def _open_research(self) -> None:
        self._push_or_replace(ResearchScreen(), route="research")

    def _cmd_ops(self, _cmd: str, _args: List[str]) -> Optional[str]:
        self._open_ops()
        return None

    def _open_ops(self) -> None:
        self._push_or_replace(OpsScreen(), route="ops")

    def _cmd_theme(self, _cmd: str, args: List[str]) -> str:
        themes = self.theme_manager.available()
        if not args:
            return "Themes: " + ", ".join(themes)
        theme = args[0].strip().lower()
        if theme not in themes:
            return f"Unknown theme: {theme}. Available: {', '.join(themes)}"
        self.theme_manager.apply(self, theme)
        return f"Theme set to {theme}."

    def _cmd_dashboard(self, _cmd: str, args: List[str]) -> str:
        if not args:
            return "Usage: dashboard list|save|load <name>"
        action = args[0].lower()
        if action == "list":
            names = sorted(self._custom_dashboards.keys())
            return (
                "Dashboards: " + ", ".join(names) if names else "No dashboards saved."
            )
        if action not in {"save", "load"}:
            return "Usage: dashboard list|save|load <name>"
        if len(args) < 2:
            return "Usage: dashboard list|save|load <name>"
        name = args[1]
        profile = self.config.profile
        if action == "save":
            layout = create_dashboard_from_state(self.session_state, profile, name=name)
            save_custom_dashboard(layout)
            self._custom_dashboards[name] = layout
            return f"Dashboard saved: {name}"
        layout = self._custom_dashboards.get(name)
        if not layout:
            return f"Dashboard not found: {name}"
        apply_custom_dashboard(self.session_state, profile, layout)
        return f"Dashboard loaded: {name}"

    def _cmd_select(self, _cmd: str, args: List[str]) -> str:
        if not args:
            return "Usage: select <symbol|#>"
        symbol = self._resolve_symbol(args[0])
        if not symbol:
            return "Symbol not found."
        self.set_selected_symbol(symbol)
        return f"Selected symbol: {symbol}"

    def _cmd_capture(self, _cmd: str, args: List[str]) -> str:
        if not args:
            return "Usage: capture on|off"
        value = args[0].lower()
        if value not in {"on", "off"}:
            return "Usage: capture on|off"
        enabled = value == "on"
        self.provider.set_capture_enabled(enabled)
        return f"Capture {'enabled' if enabled else 'disabled'}."

    def _cmd_secrets(self, _cmd: str, _args: List[str]) -> str:
        loc = resolve_secrets_file_path()
        path, created = ensure_env_secrets_file(loc.secrets_file)
        self.config.secrets_path = path
        save_config(self.config)
        warning = check_permissions(path)
        opened = open_in_editor(path)
        notes = []
        if created:
            notes.append("created")
        if warning:
            notes.append(warning)
        if not opened:
            notes.append("failed to open editor")
        suffix = f" ({'; '.join(notes)})" if notes else ""
        return f"Secrets file: {path}{suffix}"

    def _cmd_settings(self, _cmd: str, _args: List[str]) -> Optional[str]:
        self._open_settings()
        return None

    def _cmd_exchange(self, _cmd: str, args: List[str]) -> str:
        if not args:
            return "Usage: exchange list | exchange add <name> | exchange remove <name>"
        action = args[0].lower()
        if action == "list":
            exchanges = ", ".join(self.config.funding_exchanges) or "none"
            return f"Funding exchanges: {exchanges}"
        if action in {"add", "remove"}:
            if len(args) < 2:
                return f"Usage: exchange {action} <name>"
            updated, message = update_funding_exchanges(
                self.config.funding_exchanges, action, args[1]
            )
            self.config.funding_exchanges = updated
            save_config(self.config)
            return message
        return "Usage: exchange list | exchange add <name> | exchange remove <name>"

    def _cmd_funding(self, _cmd: str, args: List[str]) -> str:
        if not args or args[0].lower() != "refresh":
            return "Usage: funding refresh"
        self._cache["funding_refresh_requested"] = int(time.time() * 1000)
        save_cache(self._cache)
        return "Funding refresh requested."

    def _cmd_validate(self, _cmd: str, args: List[str]) -> str:
        if not args:
            return "Usage: validate <dataset> [timeframe]"
        dataset = args[0].strip()
        registry = DatasetRegistry(path=self.config.data_root / "_registry.json")
        datasets = load_datasets(registry)
        dataset_key = dataset if dataset.startswith("feed=") else f"feed={dataset}"
        if dataset_key not in datasets and dataset in datasets:
            dataset_key = dataset
        if dataset_key not in datasets:
            available = ", ".join(sorted(datasets.keys())) or "none"
            return f"Unknown dataset. Available: {available}"
        timeframe = (
            args[1] if len(args) > 1 else latest_timeframe(datasets, dataset_key)
        )
        if not timeframe:
            return f"No timeframes for dataset {dataset_key}"
        snapshot = load_latest_snapshot(registry, dataset_key, timeframe)
        if snapshot is None:
            return f"No snapshot found for {dataset_key} ({timeframe})"
        rows = extract_rows(snapshot)
        reports = run_validation(rows)
        self._push_or_replace(ValidationScreen(dataset_key, timeframe, reports))
        return ""

    def _cmd_watchlist(self, _cmd: str, args: List[str]) -> str:
        if not args:
            current = ", ".join(self.get_watchlist()) or "none"
            return f"Watchlist: {current}"
        raw = " ".join(args)
        symbols = [s.strip().upper() for s in raw.replace(" ", "").split(",") if s]
        if not symbols:
            return "Usage: watchlist BTC,ETH,SOL"
        self.set_watchlist(symbols)
        return f"Watchlist set: {', '.join(symbols)}"

    def _cmd_load(self, _cmd: str, args: List[str]) -> str:
        if not args:
            return "Usage: load <stream>"
        stream = args[0].lower()
        self._refresh_screen()
        return f"Loaded stream: {stream}"

    def _cmd_refresh(self, _cmd: str, _args: List[str]) -> str:
        refreshed = self._refresh_screen()
        return "Data refreshed." if refreshed else "Nothing to refresh."

    def _cmd_anomaly(self, _cmd: str, _args: List[str]) -> str:
        result = self._run_anomaly_scan()
        if not result:
            return "No anomalies detected."
        return "Anomalies: " + ", ".join(result)

    def _cmd_backtest(self, _cmd: str, _args: List[str]) -> str:
        result = backtest_run_command(_args)
        # After submitting a run, open the Research screen so the user can
        # track the job and inspect results without a separate :jobs command.
        if _args:
            self._open_research()
        return result or ""

    def _cmd_mc(self, _cmd: str, _args: List[str]) -> str:
        if not _args:
            return "Usage: mc --run-id <id> [--root PATH] [--runs N] [--seed N]"
        run_id = None
        root = JOB_ROOT
        runs = 100
        seed = 0
        if "--run-id" in _args:
            try:
                i = _args.index("--run-id")
                run_id = _args[i + 1]
            except Exception:
                return "Error: invalid --run-id usage"
        if "--root" in _args:
            try:
                i = _args.index("--root")
                root = _args[i + 1]
            except Exception:
                return "Error: invalid --root usage"
        if "--runs" in _args:
            try:
                i = _args.index("--runs")
                runs = int(_args[i + 1])
            except Exception:
                return "Error: invalid --runs usage"
        if "--seed" in _args:
            try:
                i = _args.index("--seed")
                seed = int(_args[i + 1])
            except Exception:
                return "Error: invalid --seed usage"
        if not run_id:
            return "Usage: mc --run-id <id> [--root PATH] [--runs N] [--seed N]"
        run_dir = Path(root) / run_id
        if not run_dir.exists():
            return f"Run not found: {run_id}"
        try:
            res = read_result(str(run_dir))
        except Exception as exc:
            return f"Error reading run: {exc}"
        curve = res.get("equity_curve") or []
        if len(curve) < 2:
            return "Run has insufficient equity data."
        returns = []
        for i in range(1, len(curve)):
            prev = curve[i - 1]
            if prev:
                returns.append((curve[i] - prev) / prev)
            else:
                returns.append(0.0)
        mc = resample_paths(returns, runs=runs, seed=seed, starting_value=float(curve[0]))
        self._pending_mc_result = (run_id, mc)
        self._open_research()
        return f"MC complete: runs={runs} p50_end={mc.percentiles['p50'][-1]:.2f}"

    def _cmd_bt_export(self, _cmd: str, _args: List[str]) -> str:
        return "Backtest export not available yet."

    def _cmd_mc_export(self, _cmd: str, _args: List[str]) -> str:
        return "Monte Carlo export not available yet."

    def _cmd_export(self, _cmd: str, args: List[str]) -> str:
        if not args:
            return "Usage: export <panel> <format>"
        panel = args[0]
        fmt = args[1].lower() if len(args) > 1 else "txt"
        try:
            path = self._export_screen(panel, fmt)
            return f"Exported to {path}"
        except Exception as exc:
            self._record_error(f"export failed: {exc}")
            return f"Export failed: {exc}"

    def _cmd_log_export(self, _cmd: str, _args: List[str]) -> str:
        try:
            path = self._export_logs()
            return f"Logs exported to {path}"
        except Exception as exc:
            self._record_error(f"log export failed: {exc}")
            return f"Log export failed: {exc}"

    def _cmd_inspect(self, _cmd: str, args: List[str]) -> str:
        target = args[0] if args else "current"
        return f"No diagnostics available for {target}."

    def _cmd_metrics(self, _cmd: str, args: List[str]) -> str:
        target = args[0] if args else "current"
        return f"No metrics available for {target}."

    def _cmd_alerts(self, _cmd: str, args: List[str]) -> str:
        if not args:
            if not self.alert_store.alerts:
                return "No alerts."
            lines = []
            for alert in self.alert_store.alerts[-10:]:
                lines.append(
                    f"{alert.severity.value.upper()} {alert.alert_type} ({alert.source_feed})"
                )
            return "\n".join(lines)
        action = args[0].lower()
        if action == "clear":
            self.alert_store.clear()
            return "Alerts cleared."
        if action == "mute":
            self.alert_store.set_muted(True)
            return "Alerts muted."
        if action == "unmute":
            self.alert_store.set_muted(False)
            return "Alerts unmuted."
        return "Usage: alerts [clear|mute|unmute]"

    def _cmd_errors(self, _cmd: str, _args: List[str]) -> str:
        if not self._errors:
            return "No recent errors."
        return "\n".join(self._errors[-5:])

    def _cmd_config(self, _cmd: str, _args: List[str]) -> str:
        cfg = self.config
        return (
            f"profile={cfg.profile} | mode={cfg.mode} | data_root={cfg.data_root} "
            f"| config_path={cfg.config_path}"
        )

    def _cmd_whalefilter(self, _cmd: str, args: List[str]) -> str:
        if not args:
            return "Usage: whalefilter side=<buy|sell|all> min=<notional>"
        side = "all"
        min_notional = None
        for token in args:
            if token.startswith("side="):
                side = token.split("=", 1)[1].strip().lower() or "all"
            elif token.startswith("min="):
                try:
                    min_notional = float(token.split("=", 1)[1])
                except (TypeError, ValueError):
                    min_notional = None
        if min_notional is None:
            return "Usage: whalefilter side=<buy|sell|all> min=<notional>"
        try:
            screen = self.screen
        except Exception:
            return "Whale screen not active."
        if hasattr(screen, "update_filter"):
            screen.update_filter(side, min_notional)
            return f"Whale filter set: side={side} min={min_notional}"
        return "Whale screen not active."

    def _cmd_wallet(self, _cmd: str, args: List[str]) -> str:
        if not args:
            return "Usage: wallet <#|address>"
        token = args[0].strip()
        address = None
        if token.isdigit():
            idx = int(token) - 1
            wallets = self.get_wallets()
            if 0 <= idx < len(wallets):
                address = wallets[idx]
        else:
            address = token
        if not address:
            return "Wallet not found."
        from tui.ui.screens.wallet_detail import WalletDetailScreen

        self._push_or_replace(WalletDetailScreen(address, source="whales"))
        return ""

    def _open_route(self, route: Route) -> None:
        if route.kind == "home":
            self._go_home()
            return
        if route.kind == "profile":
            self._open_profile(route.name or "")
            return
        if route.kind == "view":
            self._open_view(route.name or "")
            return
        self._set_command_message("Unknown route.")

    def _open_profile(self, name: str) -> None:
        name = name.strip().lower()
        if not name:
            self._set_command_message("Profile name required.")
            return
        if name == "liquidation":
            name = "liquidation_hunter"
        if name == "liquidations":
            name = "liquidation_hunter"
        try:
            profile = get_profile(name)
        except KeyError:
            self._set_command_message(f"Unknown profile: {name}")
            return
        self._cache["last_profile"] = profile.name
        self.session_state.active_profile = profile.name
        save_session_state(self.session_state)
        self.theme_manager.set_active_profile(profile.name)
        self.apply_palette(self.theme_manager.current())
        self._push_or_replace(
            self._build_profile_screen(profile.name, profile.label),
            route=f"profile/{profile.name}",
        )

    def _open_view(self, name: str) -> None:
        name = name.strip().lower()
        view_map = {
            "time": LiquidationTimeSeriesView,
            "heatmap": LiquidationHeatmapView,
            "heat": LiquidationHeatmapView,
            "table": LiquidationTableView,
        }
        screen_cls = view_map.get(name)
        if not screen_cls:
            self._set_command_message("Unknown view. Use: time, heatmap, table.")
            return
        recent = self._cache.setdefault("recent_views", [])
        view_label = f"liquidations/{name}"
        if view_label in recent:
            recent.remove(view_label)
        recent.insert(0, view_label)
        self._cache["recent_views"] = recent[:5]
        save_cache(self._cache)
        self._push_or_replace(screen_cls(), route=f"view/{name}")

    def _open_settings(self) -> None:
        self._push_or_replace(SettingsScreen(), route="settings")

    def _build_profile_screen(self, name: str, label: str):
        if name == "day_trader":
            return DayTraderScreen()
        if name == "liquidation_hunter":
            return LiquidationHunterScreen()
        if name == "whale_watcher":
            return WhaleWatcherScreen()
        if name == "funding_arbitrage":
            return FundingArbitrageScreen()
        return PlaceholderProfileScreen(name, label)

    def _go_home(self) -> None:
        while len(self._tt_screen_stack) > 1:
            try:
                self.pop_screen()
            except Exception:
                break
            self._tt_screen_stack.pop()
        self._sync_open_screen_order()
        if not self._tt_screen_stack:
            self._push_screen(HomeScreen(), route="home")
        self._apply_palette_to_screen(self.theme_manager.current())

    def _push_screen(self, screen, route: str | None = None) -> None:
        self.push_screen(screen)
        screen_id = screen.id or ""
        self._tt_screen_stack.append(screen_id)
        self._screen_titles[screen_id] = getattr(screen, "screen_title", screen_id)
        if route:
            self._screen_routes[screen_id] = route
        self._sync_open_screen_order()
        self._apply_palette_to_screen(self.theme_manager.current())

    def _push_or_replace(self, screen, route: str | None = None) -> None:
        if len(self._tt_screen_stack) > 1:
            try:
                self.pop_screen()
            except Exception:
                pass
            if self._tt_screen_stack:
                self._tt_screen_stack.pop()
        self._push_screen(screen, route=route)

    def _resolve_symbol(self, token: str) -> Optional[str]:
        token = token.strip()
        if not token:
            return None
        if token.isdigit():
            idx = int(token) - 1
            if 0 <= idx < len(self._top_symbols):
                return self._top_symbols[idx].upper()
        return token.upper()

    def set_top_symbols(self, symbols: List[str]) -> None:
        self._top_symbols = symbols

    def set_selected_symbol(self, symbol: str) -> None:
        symbol = symbol.upper()
        self.selected_symbol = symbol
        self._cache.setdefault("selected_symbol", {})["liquidation_hunter"] = symbol
        profile_state = get_profile_state(self.session_state, "liquidation_hunter")
        profile_state.selected_symbol = symbol
        save_session_state(self.session_state)
        save_cache(self._cache)

    def cache_snapshot(self, profile: str, key: str, snapshot) -> None:
        self._cache.setdefault("snapshots", {}).setdefault(profile, {})[key] = (
            snapshot.to_dict()
        )
        save_cache(self._cache)

    def _load_selected_symbol(self) -> str:
        profile_state = get_profile_state(self.session_state, "liquidation_hunter")
        if profile_state.selected_symbol:
            return profile_state.selected_symbol.upper()
        cached = self._cache.get("selected_symbol", {}).get("liquidation_hunter")
        return str(cached or "BTC").upper()

    def get_watchlist(self) -> List[str]:
        watchlist = self._cache.get("watchlist")
        if isinstance(watchlist, list) and watchlist:
            return [str(s).upper() for s in watchlist]
        return ["BTC", "ETH", "SOL"]

    def set_watchlist(self, symbols: List[str]) -> None:
        self._cache["watchlist"] = [str(s).upper() for s in symbols if s]
        save_cache(self._cache)
        try:
            screen = self.screen
        except Exception:
            return
        if hasattr(screen, "update_watchlist"):
            try:
                screen.update_watchlist(self._cache["watchlist"])
            except Exception:
                pass

    def get_wallets(self) -> List[str]:
        wallets = self._cache.get("wallets")
        if isinstance(wallets, list):
            return [str(w) for w in wallets]
        return []

    def set_wallets(self, wallets: List[str]) -> None:
        self._cache["wallets"] = [str(w) for w in wallets if w]
        save_cache(self._cache)

    def _load_cached_snapshots(self) -> None:
        from tui.models.liquidations import LiquidationSnapshot

        snapshots = self._cache.get("snapshots", {})
        liq = snapshots.get("liquidation_hunter", {}).get("snapshot")
        if isinstance(liq, dict):
            try:
                self.state_store.update_snapshot(
                    "liquidation_hunter",
                    "snapshot",
                    LiquidationSnapshot.from_payload(liq),
                )
            except Exception:
                pass

    def _record_error(self, message: str) -> None:
        self._errors.append(message)

    def _warn_legacy_secrets_path(self) -> None:
        try:
            legacy_path = legacy_secrets_file_path()
        except Exception:
            legacy_path = None
        if not legacy_path:
            return
        if self._cache.get("legacy_secrets_warned"):
            return
        canonical = canonical_secrets_file_path()
        try:
            self.notify(
                "Legacy secrets file detected. Update your key at: "
                f"{canonical} (legacy file: {legacy_path})",
                severity="warning",
            )
        except Exception:
            pass
        self._cache["legacy_secrets_warned"] = True
        save_cache(self._cache)

    def _toggle_sidebar(self) -> bool:
        self.sidebar_hidden = not self.sidebar_hidden
        self._cache["sidebar_hidden"] = self.sidebar_hidden
        save_cache(self._cache)
        try:
            sidebar = self.screen.query_one("#sidebar")
            sidebar.display = not self.sidebar_hidden
        except Exception:
            pass
        return self.sidebar_hidden

    def _refresh_screen(self) -> bool:
        screen = self.screen
        try:
            if hasattr(screen, "_tick"):
                screen._tick()
                return True
            if hasattr(screen, "_render"):
                screen._render()
                return True
        except Exception as exc:
            self._record_error(f"refresh failed: {exc}")
        return False

    def _run_anomaly_scan(self) -> List[str]:
        screen = self.screen
        state = getattr(screen, "_state", None)
        history = getattr(state, "price_history", None) if state else None
        if not isinstance(history, dict):
            return []
        flagged: List[str] = []
        for symbol, series in history.items():
            if not isinstance(series, list) or len(series) < 5:
                continue
            last = series[-1]
            avg = sum(series[-5:]) / 5
            if avg and abs(last - avg) / avg > 0.02:
                flagged.append(symbol)
        return flagged

    def _export_screen(self, panel: str, fmt: str) -> Path:
        base = self.config.data_root / "exports"
        base.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        filename = f"{panel}_{ts}.{fmt}"
        path = base / filename
        body = ""
        try:
            body_widget = self.screen.query_one("#screen_body")
            body = str(body_widget.renderable or "")
        except Exception:
            body = ""
        if fmt == "json":
            lines = [line for line in body.splitlines() if line]
            path.write_text(
                json.dumps({"panel": panel, "lines": lines}, indent=2), encoding="utf-8"
            )
        elif fmt == "csv":
            lines = [line.replace(",", " ") for line in body.splitlines()]
            path.write_text("\n".join(["line", *lines]), encoding="utf-8")
        else:
            path.write_text(body, encoding="utf-8")
        return path

    def _export_logs(self) -> Path:
        base = self.config.data_root / "exports"
        base.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        path = base / f"command_history_{ts}.json"
        path.write_text(
            json.dumps({"history": list(self._command_history)}, indent=2),
            encoding="utf-8",
        )
        return path

    def _sync_open_screen_order(self) -> None:
        order = [sid for sid in self._tt_screen_stack if sid]
        seen = set()
        unique: List[str] = []
        for sid in order:
            if sid not in seen:
                unique.append(sid)
                seen.add(sid)
        self._open_screen_order = unique
        self._cache["open_screens_order"] = list(unique)
        save_cache(self._cache)

    def get_open_screens(self) -> List[dict]:
        if not self._open_screen_order:
            self._sync_open_screen_order()
        entries = []
        for sid in self._open_screen_order:
            label = self._screen_titles.get(sid, sid)
            entries.append({"key": sid, "label": label})
        return entries

    def switch_to_screen_id(self, screen_id: str) -> None:
        if screen_id in self._tt_screen_stack:
            while self._tt_screen_stack and self._tt_screen_stack[-1] != screen_id:
                try:
                    self.pop_screen()
                except Exception:
                    break
                self._tt_screen_stack.pop()
            self._sync_open_screen_order()
            self._apply_palette_to_screen(self.theme_manager.current())
            return
        if screen_id == "research":
            self._open_research()
            return
        if screen_id == "ops":
            self._open_ops()
            return
        route = self._screen_routes.get(screen_id)
        if route:
            self._open_route(parse_route(route))


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TickerTape TUI")
    parser.add_argument("--setup", action="store_true", help="Run setup wizard")
    parser.add_argument("--profile", help="Start in profile")
    parser.add_argument("--data-root", help="Override data root")
    parser.add_argument("--secrets", help="Override secrets file path")
    parser.add_argument("--offline", action="store_true", help="Force offline mode")
    return parser.parse_args(argv)


def run() -> None:
    args = _parse_args(sys.argv[1:])
    overrides = {}
    if args.profile:
        overrides["profile"] = args.profile
    if args.data_root:
        overrides["data_root"] = args.data_root
    if args.secrets:
        overrides["secrets_path"] = args.secrets
        os.environ["TICKERTAPE_SECRETS_PATH"] = str(args.secrets)
    if args.offline:
        overrides["mode"] = "offline_demo"
    config = load_config(overrides)
    ensure_data_root(config)
    secrets_loc = resolve_secrets_file_path()
    secrets_path, created = ensure_env_secrets_file(secrets_loc.secrets_file)
    config.secrets_path = secrets_path
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
    if created:
        notice = f"Secrets file created at {secrets_path}"
        print(notice)
        app.secrets_notice = notice
    app._show_wizard = args.setup or config_needs_setup(config)
    app.run()


if __name__ == "__main__":
    run()
