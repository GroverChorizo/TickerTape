"""Home screen with profile navigation."""
from __future__ import annotations

from tui.ui.screens.base import BaseScreen
from tui.state.profiles import list_profiles


class HomeScreen(BaseScreen):
    def __init__(self) -> None:
        super().__init__(screen_id="home", title="Home", context="home")

    def on_mount(self) -> None:
        self.set_header("Home | TickerTape")
        self.set_status("Type 'help' for commands. Use 'profile <name>' or 'profile/<name>' to open a profile.")
        lines = ["Available profiles:"]
        for profile in list_profiles():
            lines.append(f"- {profile.name}: {profile.description}")
        cache = getattr(self.app, "_cache", {}) or {}
        recent = cache.get("recent_views") or []
        lines.append("")
        lines.append("Recent views:")
        if recent:
            for view in recent:
                lines.append(f"- {view}")
        else:
            lines.append("- (none)")
        self.body.update("\n".join(lines))
