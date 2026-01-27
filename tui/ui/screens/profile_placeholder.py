"""Placeholder screen for profiles not yet implemented."""
from __future__ import annotations

from tui.ui.screens.base import BaseScreen


class PlaceholderProfileScreen(BaseScreen):
    def __init__(self, profile_name: str, label: str) -> None:
        super().__init__(screen_id=f"profile_{profile_name}", title=label, context="profile")
        self._profile_name = profile_name
        self._label = label

    def on_mount(self) -> None:
        self.set_header(f"{self._label} | Coming Soon")
        self.set_status("This profile is not implemented yet. Type 'home' to return.")
        lines = [
            f"{self._label} is planned but not wired yet.",
            "Use `home` to return, or `help` for commands.",
        ]
        self.body.update("\n".join(lines))
