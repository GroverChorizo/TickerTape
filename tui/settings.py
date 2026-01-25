"""Settings screen for the TUI."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Static

from .themes import list_themes


class SettingsScreen(Screen):
    BINDINGS = [("escape", "close", "Close")]

    def compose(self) -> ComposeResult:
        with Vertical(id="settings"):
            yield Static("Settings", id="settings_title")
            yield Static("Appearance → Theme", id="settings_section")
            for theme in list_themes():
                yield Button(f"{theme.theme_id} — {theme.name}", id=f"theme_{theme.theme_id}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        theme_id = event.button.id.replace("theme_", "")
        if hasattr(self.app, "apply_theme"):
            getattr(self.app, "apply_theme")(theme_id, persist=True)
        self.dismiss(True)
