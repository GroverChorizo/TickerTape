"""TickerTape multi-screen, command-driven TUI."""

from __future__ import annotations

import argparse
import shlex
import sys
import time
from pathlib import Path
from typing import List, Optional

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

from config.secrets import (
    check_permissions,
    ensure_secrets_file,
    open_in_editor,
    resolve_secrets_path,
)
from tui.core.cache import load_cache, save_cache
from tui.core.commands import CommandRegistry
from tui.core.router import Route, parse_route
from tui.core.state import StateStore
from tui.providers.hyperliquid import HyperliquidProvider
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
from tui.ui.screens.home import HomeScreen
from tui.ui.screens.profile_liquidation import LiquidationHunterScreen
from tui.ui.screens.profile_placeholder import PlaceholderProfileScreen
from tui.ui.screens.settings import SettingsScreen
from tui.ui.screens.validation import ValidationScreen
from tui.ui.screens.views import (
    LiquidationHeatmapView,
    LiquidationTableView,
    LiquidationTimeSeriesView,
)
from backend.storage import DatasetRegistry
from backend.query_helpers import load_latest_snapshot
from tui.state.datasets import latest_timeframe, load_datasets
from tui.validation import extract_rows, run_validation


class TickerTapeApp(App):
    CSS_PATH = "tui.css"
    BINDINGS = [
        ("ctrl+p", "focus_command", "Focus command"),
        ("ctrl+h", "go_home", "Home"),
        ("ctrl+comma", "open_settings", "Settings"),
    ]

    def __init__(self, config: TuiConfig) -> None:
        super().__init__()
        self.config = config
        self.secrets_notice: Optional[str] = None
        self.state_store = StateStore()
        self.command_registry = CommandRegistry()
        self.session_state = load_session_state()
        self.theme_manager = ThemeManager(self.session_state)
        self._cache = load_cache()
        self._cache.setdefault("preferences", {"refresh_interval_s": 1.0})
        self._tt_screen_stack: List[str] = []
        self._command_history: List[str] = []
        self._history_index: int = 0
        self._top_symbols: List[str] = []
        self.selected_symbol = self._load_selected_symbol()
        registry_path = self.config.data_root / "_registry.json"
        self.provider = HyperliquidProvider(
            registry=DatasetRegistry(path=registry_path),
            offline=self.config.mode == "offline_demo",
        )
        self._register_commands()
        self._load_cached_snapshots()

    def on_mount(self) -> None:
        self.apply_palette(self.theme_manager.current())
        self._push_screen(HomeScreen())
        if self.secrets_notice:
            self.notify(self.secrets_notice, severity="information")
        if getattr(self, "_show_wizard", False):
            self.notify(
                "Setup required. Run with --setup to configure.", severity="warning"
            )

    def on_shutdown(self) -> None:
        try:
            self.provider.close()
        except Exception:
            pass
        save_cache(self._cache)

    def apply_palette(self, palette) -> None:
        self.styles.background = palette.bg.primary
        self.styles.color = palette.text.primary
        self._apply_palette_to_screen(palette)

    def _apply_palette_to_screen(self, palette) -> None:
        try:
            header = self.screen.query_one("#screen_header")
            header.styles.background = palette.bg.panel
            header.styles.color = palette.accent.cyan
        except Exception:
            pass
        try:
            status = self.screen.query_one("#status_strip")
            status.styles.color = palette.text.muted
        except Exception:
            pass
        try:
            body = self.screen.query_one("#screen_body")
            body.styles.background = palette.bg.primary
            body.styles.color = palette.text.primary
        except Exception:
            pass
        try:
            command = self.screen.query_one("#command")
            command.styles.background = palette.bg.panel
            command.styles.color = palette.text.primary
        except Exception:
            pass
        try:
            cmd_status = self.screen.query_one("#command_status")
            cmd_status.styles.color = palette.text.muted
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

    def _register_commands(self) -> None:
        self.command_registry.register(
            "help", "Show commands for this screen.", self._cmd_help
        )
        self.command_registry.register(
            "home", "Return to the home screen.", self._cmd_home, aliases=["/"]
        )
        self.command_registry.register(
            "profile", "Open a profile screen.", self._cmd_profile
        )
        self.command_registry.register(
            "view", "Open a data view screen.", self._cmd_view
        )
        self.command_registry.register(
            "diagnostics", "Run connectivity diagnostics.", self._cmd_diagnostics
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

    def _cmd_help(self, _cmd: str, _args: List[str]) -> str:
        context = getattr(self.screen, "command_context", "home")
        lines = self.command_registry.help_for(context)
        if not lines:
            return "No commands registered."
        return "\n".join(lines)

    def _cmd_home(self, _cmd: str, _args: List[str]) -> Optional[str]:
        self._go_home()
        return None

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

    def _cmd_diagnostics(self, _cmd: str, _args: List[str]) -> str:
        report = self.provider.diagnostics()
        http = report.get("http", "unknown")
        ws = report.get("ws", "not configured")
        return f"Diagnostics: http={http} | ws={ws}"

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
        resolved = resolve_secrets_path(self.config.secrets_path)
        path, created = ensure_secrets_file(resolved)
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
        self._push_or_replace(self._build_profile_screen(profile.name, profile.label))

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
        self._push_or_replace(screen_cls())

    def _open_settings(self) -> None:
        self._push_or_replace(SettingsScreen())

    def _build_profile_screen(self, name: str, label: str):
        if name == "liquidation_hunter":
            return LiquidationHunterScreen()
        return PlaceholderProfileScreen(name, label)

    def _go_home(self) -> None:
        while len(self._tt_screen_stack) > 1:
            try:
                self.pop_screen()
            except Exception:
                break
            self._tt_screen_stack.pop()
        if not self._tt_screen_stack:
            self._push_screen(HomeScreen())
        self._apply_palette_to_screen(self.theme_manager.current())

    def _push_screen(self, screen) -> None:
        self.push_screen(screen)
        self._tt_screen_stack.append(screen.id or "")
        self._apply_palette_to_screen(self.theme_manager.current())

    def _push_or_replace(self, screen) -> None:
        if len(self._tt_screen_stack) > 1:
            try:
                self.pop_screen()
            except Exception:
                pass
            if self._tt_screen_stack:
                self._tt_screen_stack.pop()
        self._push_screen(screen)

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
    if args.offline:
        overrides["mode"] = "offline_demo"
    config = load_config(overrides)
    ensure_data_root(config)
    secrets_path = resolve_secrets_path(config.secrets_path)
    secrets_path, created = ensure_secrets_file(secrets_path)
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
