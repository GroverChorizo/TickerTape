"""Startup wizard for first-run setup."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Static

from config.secrets import DEFAULT_SECRETS_PATH, ensure_secrets_file
from tui.state.profiles import list_profiles
from tui.state.session import get_profile_state, load_session_state, save_session_state
from .bootstrap import bootstrap_data
from .config import (
    TuiConfig,
    DEFAULT_DATA_ROOT,
    DEFAULT_PROFILE,
    ensure_data_root,
    save_config,
)
from .themes.theme_manager import ThemeManager


@dataclass
class WizardState:
    mode: str = "offline_demo"
    data_root: Path = DEFAULT_DATA_ROOT
    secrets_path: Optional[Path] = None
    profile: str = DEFAULT_PROFILE
    theme: str = ""
    panels: list[str] = field(default_factory=list)
    alerts: dict[str, bool] = field(default_factory=dict)


class StartupWizard(Screen):
    BINDINGS = [
        ("escape", "close", "Close"),
        ("up", "previous_option", "Previous"),
        ("down", "next_option", "Next"),
    ]

    def __init__(self, config_path: Path) -> None:
        super().__init__()
        self.state = WizardState()
        self.config_path = config_path
        self.step = 0
        self._profile_index = 0
        self._theme_index = 0
        self._panel_index = 0
        self._alert_index = 0
        self._profiles: list = []
        self._themes: list[str] = []
        self._panel_options: list[str] = []
        self._panel_enabled: set[str] = set()
        self._alert_options = [
            "liquidation_cascades",
            "whale_trades",
            "funding_extremes",
            "anomaly_spikes",
        ]
        self._alert_enabled: set[str] = set()

    def compose(self) -> ComposeResult:
        with Vertical(id="wizard"):
            yield Static(id="wizard_title")
            yield Static(id="wizard_body")
            yield Input(placeholder="", id="wizard_input")
            yield Button("Back", id="wizard_back")
            yield Button("Next", id="wizard_next")

    def on_mount(self) -> None:
        self._profiles = list_profiles()
        self._themes = ThemeManager().available()
        self._sync_profile_defaults()
        self._render_step()

    def _render_step(self) -> None:
        title = self.query_one("#wizard_title", Static)
        body = self.query_one("#wizard_body", Static)
        input_field = self.query_one("#wizard_input", Input)
        input_field.value = ""
        input_field.display = True
        if self.step == 0:
            title.update("Step 1/6: Welcome")
            body.update(
                "Welcome to TickerTape. This wizard will help you pick a profile, theme, panels, alerts, and secrets."
            )
            input_field.display = False
        elif self.step == 1:
            title.update("Step 2/6: Profile Selection")
            input_field.display = False
            lines = ["Select a profile (use ↑/↓)."]
            if not self._profiles:
                lines.append("No profiles available.")
            else:
                self._profile_index = max(
                    0, min(self._profile_index, len(self._profiles) - 1)
                )
                for idx, profile in enumerate(self._profiles):
                    marker = "▶" if idx == self._profile_index else " "
                    lines.append(f"{marker} {profile.label} ({profile.name})")
            body.update("\n".join(lines))
        elif self.step == 2:
            title.update("Step 3/6: Theme Selection")
            input_field.display = False
            lines = ["Select a theme (use ↑/↓)."]
            if not self._themes:
                lines.append("No themes available.")
            else:
                self._theme_index = max(
                    0, min(self._theme_index, len(self._themes) - 1)
                )
                for idx, theme_id in enumerate(self._themes):
                    marker = "▶" if idx == self._theme_index else " "
                    lines.append(f"{marker} {theme_id}")
            body.update("\n".join(lines))
        elif self.step == 3:
            title.update("Step 4/6: Dashboard Customization")
            input_field.display = False
            lines = ["Toggle panels (Space) and use ↑/↓ to navigate."]
            if not self._panel_options:
                lines.append("No panels available.")
            else:
                self._panel_index = max(
                    0, min(self._panel_index, len(self._panel_options) - 1)
                )
                for idx, panel in enumerate(self._panel_options):
                    marker = "▶" if idx == self._panel_index else " "
                    checked = "[x]" if panel in self._panel_enabled else "[ ]"
                    lines.append(f"{marker} {checked} {panel}")
            body.update("\n".join(lines))
        elif self.step == 4:
            title.update("Step 5/6: Alerts Configuration")
            input_field.display = False
            lines = ["Toggle alerts (Space) and use ↑/↓ to navigate."]
            self._alert_index = max(
                0, min(self._alert_index, len(self._alert_options) - 1)
            )
            for idx, alert in enumerate(self._alert_options):
                marker = "▶" if idx == self._alert_index else " "
                checked = "[x]" if alert in self._alert_enabled else "[ ]"
                lines.append(f"{marker} {checked} {alert}")
            body.update("\n".join(lines))
        elif self.step == 5:
            title.update("Step 6/6: Paths & Secrets")
            body.update(
                "Set BASE_PARQUET_ROOT (default: ./data/parquet).\n"
                f"Secrets file default: {DEFAULT_SECRETS_PATH}\n"
                "Optional: enter secrets path (leave blank to use default and create it).\n"
                "Format: <data_root> [| <secrets_path>]\n\n"
                f"Profile: {self.state.profile}\n"
                f"Theme: {self.state.theme or 'default'}\n"
                f"Panels: {', '.join(self._selected_panels()) or 'default'}\n"
                f"Alerts: {', '.join(sorted(self._alert_enabled)) or 'none'}"
            )
            input_field.placeholder = (
                f"{self.state.data_root} | {self.state.secrets_path or ''}".strip()
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "wizard_back":
            self.step = max(0, self.step - 1)
            self.query_one("#wizard_input", Input).display = True
            self._render_step()
            return
        if event.button.id == "wizard_next":
            self._handle_next()

    def _handle_next(self) -> None:
        input_field = self.query_one("#wizard_input", Input)
        value = input_field.value.strip()
        if self.step == 0:
            self.state.mode = "offline_demo"
        elif self.step == 1:
            if self._profiles:
                self.state.profile = self._profiles[self._profile_index].name
                self._sync_profile_defaults()
        elif self.step == 2:
            if self._themes:
                self.state.theme = self._themes[self._theme_index]
        elif self.step == 3:
            self.state.panels = self._selected_panels()
        elif self.step == 4:
            self.state.alerts = {
                alert: alert in self._alert_enabled for alert in self._alert_options
            }
        elif self.step == 5:
            data_root, secrets = _parse_paths_input(value, self.state)
            self.state.data_root = data_root
            if secrets is None:
                secrets = DEFAULT_SECRETS_PATH
            self.state.secrets_path = ensure_secrets_file(secrets)[0]
            config = TuiConfig(
                mode=self.state.mode,
                data_root=self.state.data_root,
                profile=self.state.profile or DEFAULT_PROFILE,
                secrets_path=self.state.secrets_path,
                alerts=self.state.alerts,
                panel_overrides={self.state.profile: self._selected_panels()}
                if self._selected_panels()
                else {},
                config_path=self.config_path,
            )
            ensure_data_root(config)
            save_config(config)
            bootstrap_data(config)
            session_state = load_session_state()
            session_state.active_profile = config.profile
            profile_state = get_profile_state(session_state, config.profile)
            if self._selected_panels():
                profile_state.panel_order = list(self._selected_panels())
            save_session_state(session_state)
            if self.state.theme:
                ThemeManager().apply(self.app, self.state.theme)
            self.dismiss(True)
            return
        self.step += 1
        self._render_step()

    def action_previous_option(self) -> None:
        if self.step == 1 and self._profiles:
            self._profile_index = (self._profile_index - 1) % len(self._profiles)
        elif self.step == 2 and self._themes:
            self._theme_index = (self._theme_index - 1) % len(self._themes)
        elif self.step == 3 and self._panel_options:
            self._panel_index = (self._panel_index - 1) % len(self._panel_options)
        elif self.step == 4 and self._alert_options:
            self._alert_index = (self._alert_index - 1) % len(self._alert_options)
        else:
            return
        self._render_step()

    def action_next_option(self) -> None:
        if self.step == 1 and self._profiles:
            self._profile_index = (self._profile_index + 1) % len(self._profiles)
        elif self.step == 2 and self._themes:
            self._theme_index = (self._theme_index + 1) % len(self._themes)
        elif self.step == 3 and self._panel_options:
            self._panel_index = (self._panel_index + 1) % len(self._panel_options)
        elif self.step == 4 and self._alert_options:
            self._alert_index = (self._alert_index + 1) % len(self._alert_options)
        else:
            return
        self._render_step()

    def on_key(self, event) -> None:
        if event.key != "space":
            return
        if self.step == 3 and self._panel_options:
            panel = self._panel_options[self._panel_index]
            if panel in self._panel_enabled:
                self._panel_enabled.remove(panel)
            else:
                self._panel_enabled.add(panel)
            self._render_step()
        if self.step == 4 and self._alert_options:
            alert = self._alert_options[self._alert_index]
            if alert in self._alert_enabled:
                self._alert_enabled.remove(alert)
            else:
                self._alert_enabled.add(alert)
            self._render_step()

    def _sync_profile_defaults(self) -> None:
        if not self._profiles:
            return
        profile = self._profiles[self._profile_index]
        self.state.profile = profile.name
        self._panel_options = list(profile.default_panel_order)
        if not self._panel_options:
            self._panel_options = list(profile.focus_panels)
        self._panel_enabled = set(self._panel_options)

    def _selected_panels(self) -> list[str]:
        if not self._panel_options:
            return []
        return [panel for panel in self._panel_options if panel in self._panel_enabled]


def _parse_paths_input(value: str, state: WizardState) -> tuple[Path, Optional[Path]]:
    if not value:
        return state.data_root, state.secrets_path
    parts = [part.strip() for part in value.split("|", maxsplit=1)]
    data_root = Path(parts[0]) if parts[0] else state.data_root
    secrets = None
    if len(parts) > 1 and parts[1]:
        secrets = Path(parts[1])
    return data_root, secrets
