"""Base screen for TickerTape profiles."""

from __future__ import annotations

from textual import events
from textual.screen import Screen
from textual.widgets import Static, Input
from textual.containers import Horizontal, Vertical

from tui.ui.widgets.command_bar import CommandBar
from tui.ui.layout import apply_layout
from tui.ui.sidebar import Sidebar, SidebarEntry
from tui.ui.tabbar import TabBar, TabItem
from tui.state.profiles import list_profiles
from tui.ui.fullscreen import apply_fullscreen_state, toggle_fullscreen
from tui.ui.density import apply_density_state, toggle_density


class BaseScreen(Screen):
    BINDINGS = [
        ("ctrl+p", "focus_command", "Focus command"),
        ("f", "toggle_fullscreen", "Fullscreen"),
        ("d", "toggle_density", "Density"),
    ]

    def __init__(self, *, screen_id: str, title: str, context: str) -> None:
        super().__init__(id=screen_id)
        self.screen_title = title
        self.command_context = context
        self.header = Static("", id="screen_header")
        self.status = Static("", id="status_strip")
        self.body = Static("", id="screen_body")
        self.sidebar = Sidebar(id="sidebar")
        self.tabbar = TabBar(id="tabbar")
        self.command_bar = CommandBar()

    def compose(self):
        with Vertical(id="screen_root"):
            yield self.header
            yield self.status
            with Horizontal(id="content_row"):
                yield self.sidebar
                yield self.body
            yield self.tabbar
            yield self.command_bar

    def set_header(self, text: str) -> None:
        self.header.update(text)

    def set_status(self, text: str) -> None:
        self.status.update(text)

    def on_show(self) -> None:
        layout = apply_layout(self, self.size.width)
        self._sync_navigation(layout)
        self._apply_persisted_ui_state()

    def on_resize(self, event: events.Resize) -> None:
        layout = apply_layout(self, event.size.width)
        self._sync_navigation(layout)

    def action_focus_command(self) -> None:
        try:
            self.command_bar.input.focus()
        except Exception:
            pass

    def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value.strip()
        self.command_bar.clear()
        if not command:
            return
        handler = getattr(self.app, "dispatch_command", None)
        if handler:
            handler(command, context=self.command_context)

    def action_toggle_fullscreen(self) -> None:
        self._ensure_state()
        toggle_fullscreen(self.app, self, self._profile_name())

    def action_toggle_density(self) -> None:
        self._ensure_state()
        toggle_density(self.app, self, self._profile_name())

    def _sync_navigation(self, layout: str) -> None:
        entries = [SidebarEntry(key="home", label="Home", short="H")]
        for profile in list_profiles():
            entries.append(
                SidebarEntry(
                    key=profile.name,
                    label=profile.label,
                    short=profile.label[:1].upper(),
                )
            )
        active_key = self.command_context
        if active_key not in {entry.key for entry in entries}:
            active_key = "home"
        self.sidebar.set_entries(entries)
        self.sidebar.set_active(active_key)
        compact = layout in {"layout-narrow", "layout-compact"}
        self.sidebar.set_compact(compact)

        tabs = [
            TabItem(key=entry.key, label=entry.label, short=entry.short)
            for entry in entries
        ]
        self.tabbar.set_tabs(tabs)
        self.tabbar.set_active(active_key)
        self.tabbar.display = compact

    def _apply_persisted_ui_state(self) -> None:
        self._ensure_state()
        apply_fullscreen_state(self.app, self, self._profile_name())
        apply_density_state(self.app, self, self._profile_name())

    def _ensure_state(self) -> None:
        if not hasattr(self, "app"):
            return
        if not getattr(self.app, "session_state", None):
            return

    def _profile_name(self) -> str:
        if self.command_context in {"home", "views", "settings"}:
            return self.app.session_state.active_profile
        return self.command_context
