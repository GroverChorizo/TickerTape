"""Settings screen for updating profile, theme, panels, and alerts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List

from textual import events

from tui.config import TuiConfig, save_config
from tui.state.profiles import ProfileConfig, list_profiles
from tui.state.session import SessionState, get_profile_state, save_session_state
from tui.ui.screens.base import BaseScreen


ALERT_OPTIONS = [
    "liquidation_cascades",
    "whale_trades",
    "funding_extremes",
    "anomaly_spikes",
]


@dataclass
class SettingsPayload:
    profile: str
    theme: str
    panels: List[str] = field(default_factory=list)
    alerts: Dict[str, bool] = field(default_factory=dict)


def apply_settings(
    config: TuiConfig,
    session_state: SessionState,
    payload: SettingsPayload,
    *,
    apply_theme: Callable[[str, str], None] | None = None,
) -> None:
    """Persist settings to config + session state."""
    config.profile = payload.profile
    config.alerts = dict(payload.alerts)
    panel_overrides = dict(config.panel_overrides)
    if payload.panels:
        panel_overrides[payload.profile] = list(payload.panels)
    else:
        panel_overrides.pop(payload.profile, None)
    config.panel_overrides = panel_overrides
    save_config(config)

    session_state.active_profile = payload.profile
    profile_state = get_profile_state(session_state, payload.profile)
    if payload.panels:
        profile_state.panel_order = list(payload.panels)
    save_session_state(session_state)

    if payload.theme and apply_theme:
        apply_theme(payload.profile, payload.theme)


class SettingsScreen(BaseScreen):
    """Interactive settings UI."""

    BINDINGS = [
        ("ctrl+p", "focus_command", "Focus command"),
        ("ctrl+s", "save", "Save"),
        ("escape", "cancel", "Cancel"),
        ("left", "prev_section", "Previous section"),
        ("right", "next_section", "Next section"),
        ("up", "prev_item", "Previous option"),
        ("down", "next_item", "Next option"),
    ]

    def __init__(self) -> None:
        super().__init__(screen_id="settings", title="Settings", context="settings")
        self._sections = ["profile", "theme", "panels", "alerts"]
        self._section_index = 0
        self._profiles: List[ProfileConfig] = []
        self._themes: List[str] = []
        self._profile_index = 0
        self._theme_index = 0
        self._panel_index = 0
        self._alert_index = 0
        self._panel_options: List[str] = []
        self._panel_enabled: set[str] = set()
        self._alert_enabled: set[str] = set()

    def on_mount(self) -> None:
        self._profiles = list_profiles()
        self._themes = self.app.theme_manager.available()
        self._load_from_config()
        self._render()

    def _load_from_config(self) -> None:
        config = self.app.config
        if self._profiles:
            for idx, profile in enumerate(self._profiles):
                if profile.name == config.profile:
                    self._profile_index = idx
                    break
        current_theme = self.app.theme_manager.current_id()
        if self._themes and current_theme in self._themes:
            self._theme_index = self._themes.index(current_theme)
        self._sync_profile_panels()
        self._alert_enabled = {k for k, v in (config.alerts or {}).items() if v}

    def _sync_profile_panels(self) -> None:
        if not self._profiles:
            return
        profile = self._profiles[self._profile_index]
        overrides = self.app.config.panel_overrides.get(profile.name, [])
        options = list(profile.default_panel_order or profile.focus_panels)
        self._panel_options = options
        if overrides:
            self._panel_enabled = set(overrides)
        else:
            self._panel_enabled = set(options)
        self._panel_index = min(self._panel_index, max(len(self._panel_options) - 1, 0))

    def _current_section(self) -> str:
        return self._sections[self._section_index]

    def _render(self) -> None:
        section = self._current_section()
        self.set_header("Settings - " + section.replace("_", " ").title())
        self.set_status(
            "Left/Right: section | Up/Down: navigate | Space: toggle | Ctrl+S: save | Esc: cancel"
        )
        lines: List[str] = []
        if section == "profile":
            lines.append("Select active profile:")
            if not self._profiles:
                lines.append("No profiles available.")
            else:
                self._profile_index = min(
                    self._profile_index, max(len(self._profiles) - 1, 0)
                )
                for idx, profile in enumerate(self._profiles):
                    marker = ">" if idx == self._profile_index else " "
                    lines.append(f"{marker} {profile.label} ({profile.name})")
        elif section == "theme":
            lines.append("Select theme:")
            if not self._themes:
                lines.append("No themes available.")
            else:
                self._theme_index = min(
                    self._theme_index, max(len(self._themes) - 1, 0)
                )
                for idx, theme_id in enumerate(self._themes):
                    marker = ">" if idx == self._theme_index else " "
                    lines.append(f"{marker} {theme_id}")
        elif section == "panels":
            lines.append("Toggle panels for selected profile:")
            if not self._panel_options:
                lines.append("No panels available.")
            else:
                self._panel_index = min(
                    self._panel_index, max(len(self._panel_options) - 1, 0)
                )
                for idx, panel in enumerate(self._panel_options):
                    marker = ">" if idx == self._panel_index else " "
                    checked = "[x]" if panel in self._panel_enabled else "[ ]"
                    lines.append(f"{marker} {checked} {panel}")
        elif section == "alerts":
            lines.append("Toggle alerts:")
            self._alert_index = min(self._alert_index, max(len(ALERT_OPTIONS) - 1, 0))
            for idx, alert in enumerate(ALERT_OPTIONS):
                marker = ">" if idx == self._alert_index else " "
                checked = "[x]" if alert in self._alert_enabled else "[ ]"
                lines.append(f"{marker} {checked} {alert}")
        self.body.update("\n".join(lines))

    def action_prev_section(self) -> None:
        self._section_index = (self._section_index - 1) % len(self._sections)
        self._render()

    def action_next_section(self) -> None:
        self._section_index = (self._section_index + 1) % len(self._sections)
        self._render()

    def action_prev_item(self) -> None:
        section = self._current_section()
        if section == "profile" and self._profiles:
            self._profile_index = (self._profile_index - 1) % len(self._profiles)
            self._sync_profile_panels()
        elif section == "theme" and self._themes:
            self._theme_index = (self._theme_index - 1) % len(self._themes)
        elif section == "panels" and self._panel_options:
            self._panel_index = (self._panel_index - 1) % len(self._panel_options)
        elif section == "alerts":
            self._alert_index = (self._alert_index - 1) % len(ALERT_OPTIONS)
        self._render()

    def action_next_item(self) -> None:
        section = self._current_section()
        if section == "profile" and self._profiles:
            self._profile_index = (self._profile_index + 1) % len(self._profiles)
            self._sync_profile_panels()
        elif section == "theme" and self._themes:
            self._theme_index = (self._theme_index + 1) % len(self._themes)
        elif section == "panels" and self._panel_options:
            self._panel_index = (self._panel_index + 1) % len(self._panel_options)
        elif section == "alerts":
            self._alert_index = (self._alert_index + 1) % len(ALERT_OPTIONS)
        self._render()

    def on_key(self, event: events.Key) -> None:
        if event.key != "space":
            return
        section = self._current_section()
        if section == "panels" and self._panel_options:
            panel = self._panel_options[self._panel_index]
            if panel in self._panel_enabled:
                self._panel_enabled.remove(panel)
            else:
                self._panel_enabled.add(panel)
            self._render()
        if section == "alerts":
            alert = ALERT_OPTIONS[self._alert_index]
            if alert in self._alert_enabled:
                self._alert_enabled.remove(alert)
            else:
                self._alert_enabled.add(alert)
            self._render()

    def action_save(self) -> None:
        profile = (
            self._profiles[self._profile_index].name if self._profiles else "day_trader"
        )
        theme = self._themes[self._theme_index] if self._themes else ""
        payload = SettingsPayload(
            profile=profile,
            theme=theme,
            panels=[p for p in self._panel_options if p in self._panel_enabled],
            alerts={alert: alert in self._alert_enabled for alert in ALERT_OPTIONS},
        )

        def _apply_theme(profile_name: str, theme_name: str) -> None:
            self.app.theme_manager.set_active_profile(profile_name)
            self.app.theme_manager.apply(self.app, theme_name)

        apply_settings(
            self.app.config, self.app.session_state, payload, apply_theme=_apply_theme
        )
        self.dismiss(True)
        if hasattr(self.app, "_open_profile"):
            self.app.call_later(self.app._open_profile, profile)

    def action_cancel(self) -> None:
        self.dismiss(False)
