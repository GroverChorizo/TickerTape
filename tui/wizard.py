"""Startup wizard for first-run setup."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Static

from config.secrets import DEFAULT_SECRETS_PATH, ensure_secrets_file
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
    theme: str = ""


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
        self._theme_index = 0
        self._themes: list[str] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="wizard"):
            yield Static(id="wizard_title")
            yield Static(id="wizard_body")
            yield Input(placeholder="", id="wizard_input")
            yield Button("Back", id="wizard_back")
            yield Button("Next", id="wizard_next")

    def on_mount(self) -> None:
        self._themes = ThemeManager().available()
        self._render_step()

    def _render_step(self) -> None:
        title = self.query_one("#wizard_title", Static)
        body = self.query_one("#wizard_body", Static)
        input_field = self.query_one("#wizard_input", Input)
        input_field.value = ""
        input_field.display = True
        if self.step == 0:
            title.update("Step 1/4: Mode Selection")
            body.update(
                "Choose mode: Offline Demo (no network), Local Ingestion (run once), Live (requires API keys).\n"
                "Enter: offline_demo | local_ingestion | live"
            )
            input_field.placeholder = "offline_demo"
        elif self.step == 1:
            title.update("Step 2/4: Theme Selection")
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
        elif self.step == 2:
            title.update("Step 3/4: Paths & Secrets")
            body.update(
                "Set BASE_PARQUET_ROOT (default: ./data/parquet).\n"
                f"Secrets file default: {DEFAULT_SECRETS_PATH}\n"
                "Optional: enter secrets path (leave blank to use default and create it).\n"
                "Format: <data_root> [| <secrets_path>]"
            )
            input_field.placeholder = (
                f"{self.state.data_root} | {self.state.secrets_path or ''}".strip()
            )
        elif self.step == 3:
            title.update("Step 4/4: Data Bootstrap")
            body.update(
                "Press Next to bootstrap data for the selected mode and launch the dashboard."
            )
            input_field.display = False

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
            self.state.mode = value or "offline_demo"
        elif self.step == 1:
            if self._themes:
                self.state.theme = self._themes[self._theme_index]
        elif self.step == 2:
            data_root, secrets = _parse_paths_input(value, self.state)
            self.state.data_root = data_root
            if secrets is None:
                secrets = DEFAULT_SECRETS_PATH
            self.state.secrets_path = ensure_secrets_file(secrets)[0]
        elif self.step == 3:
            config = TuiConfig(
                mode=self.state.mode,
                data_root=self.state.data_root,
                profile=DEFAULT_PROFILE,
                secrets_path=self.state.secrets_path,
                config_path=self.config_path,
            )
            ensure_data_root(config)
            save_config(config)
            bootstrap_data(config)
            if self.state.theme:
                ThemeManager().apply(self.app, self.state.theme)
            self.dismiss(True)
            return
        self.step += 1
        self._render_step()

    def action_previous_option(self) -> None:
        if self.step != 1 or not self._themes:
            return
        self._theme_index = (self._theme_index - 1) % len(self._themes)
        self._render_step()

    def action_next_option(self) -> None:
        if self.step != 1 or not self._themes:
            return
        self._theme_index = (self._theme_index + 1) % len(self._themes)
        self._render_step()


def _parse_paths_input(value: str, state: WizardState) -> tuple[Path, Optional[Path]]:
    if not value:
        return state.data_root, state.secrets_path
    parts = [part.strip() for part in value.split("|", maxsplit=1)]
    data_root = Path(parts[0]) if parts[0] else state.data_root
    secrets = None
    if len(parts) > 1 and parts[1]:
        secrets = Path(parts[1])
    return data_root, secrets
