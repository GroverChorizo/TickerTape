"""Startup wizard for first-run setup."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Static

from .config import TuiConfig, DEFAULT_DATA_ROOT, DEFAULT_PROFILE, ensure_data_root, save_config
from .bootstrap import bootstrap_data


@dataclass
class WizardState:
    mode: str = "offline_demo"
    data_root: Path = DEFAULT_DATA_ROOT
    secrets_path: Optional[Path] = None


class StartupWizard(Screen):
    BINDINGS = [("escape", "close", "Close")]

    def __init__(self, config_path: Path) -> None:
        super().__init__()
        self.state = WizardState()
        self.config_path = config_path
        self.step = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="wizard"):
            yield Static(id="wizard_title")
            yield Static(id="wizard_body")
            yield Input(placeholder="", id="wizard_input")
            yield Button("Back", id="wizard_back")
            yield Button("Next", id="wizard_next")

    def on_mount(self) -> None:
        self._render_step()

    def _render_step(self) -> None:
        title = self.query_one("#wizard_title", Static)
        body = self.query_one("#wizard_body", Static)
        input_field = self.query_one("#wizard_input", Input)
        input_field.value = ""
        if self.step == 0:
            title.update("Welcome / Mode Selection")
            body.update(
                "Choose mode: Offline Demo (no network), Local Ingestion (run once), Live (requires API keys).\n"
                "Enter: offline_demo | local_ingestion | live"
            )
            input_field.placeholder = "offline_demo"
        elif self.step == 1:
            title.update("Paths & Storage")
            body.update("Set BASE_PARQUET_ROOT (default: ./data/parquet).")
            input_field.placeholder = str(self.state.data_root)
        elif self.step == 2:
            title.update("Secrets / API Key Setup")
            body.update("If Live mode: enter .env path (leave blank to skip).")
            input_field.placeholder = "~/.tickertape/secrets/HLdontShare.env"
        elif self.step == 3:
            title.update("Data Bootstrap")
            body.update("Press Next to bootstrap data for the selected mode.")
            input_field.display = False
        else:
            title.update("Finish")
            body.update("Setup complete. Press Next to launch dashboard.")
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
            self.state.data_root = Path(value or self.state.data_root)
        elif self.step == 2:
            self.state.secrets_path = Path(value) if value else None
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
        else:
            self.dismiss(True)
            return
        self.step += 1
        self.query_one("#wizard_input", Input).display = True
        self._render_step()
