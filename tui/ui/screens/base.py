"""Base screen for TickerTape profiles."""

from __future__ import annotations

from textual import events
from textual.screen import Screen
from textual.widgets import Static, Input
from textual.containers import Horizontal, Vertical

from tui.ui.widgets.command_bar import CommandBar
from tui.ui.layout import apply_layout
from tui.ui.sidebar import SidebarContainer, SidebarEntry
from tui.ui.tabbar import TabBar, TabItem
from tui.ui.tab_carousel import TabCarousel, TabEntry
from tui.ui.status_bar import StatusBar
from tui.state.profiles import list_profiles
from tui.ui.fullscreen import apply_fullscreen_state, toggle_fullscreen
from tui.ui.density import apply_density_state, toggle_density


class BaseScreen(Screen):
    BINDINGS = [
        ("ctrl+p", "focus_command", "Focus command"),
        ("f", "toggle_fullscreen", "Fullscreen"),
        ("d", "toggle_density", "Density"),
        ("ctrl+left", "tab_prev", "Previous tab"),
        ("ctrl+right", "tab_next", "Next tab"),
        ("alt+1", "tab_index(1)", "Tab 1"),
        ("alt+2", "tab_index(2)", "Tab 2"),
        ("alt+3", "tab_index(3)", "Tab 3"),
        ("alt+4", "tab_index(4)", "Tab 4"),
        ("alt+5", "tab_index(5)", "Tab 5"),
        ("a", "cycle_alert_category", "Cycle alerts"),
    ]

    def __init__(self, *, screen_id: str, title: str, context: str) -> None:
        super().__init__(id=screen_id)
        self.screen_title = title
        self.command_context = context
        self.header = Static("", id="screen_header")
        self.status = StatusBar(id="status_bar")
        self._status_timer = None
        self.tab_carousel = TabCarousel(id="tab_carousel")
        self.body = Static("", id="screen_body")
        # SidebarContainer replaces the old Sidebar — same public interface,
        # but now has an alert history section below the navigation list.
        self.sidebar = SidebarContainer(id="sidebar")
        self.tabbar = TabBar(id="tabbar")
        self.command_bar = CommandBar()

    def compose(self):
        with Vertical(id="screen_root"):
            yield self.header
            yield self.status
            yield self.tab_carousel
            with Horizontal(id="content_row"):
                yield self.sidebar
                yield self.body
            yield self.tabbar
            yield self.command_bar

    def set_header(self, text: str) -> None:
        self.header.update(text)

    def set_status(self, text: str) -> None:
        self.status.set_status(text)

    def on_show(self) -> None:
        layout = apply_layout(self, self.size.width)
        self._sync_navigation(layout)
        self._apply_persisted_ui_state()
        self._start_status_timer()
        self._wire_alert_store()

    def on_hide(self) -> None:
        if self._status_timer is not None:
            self._status_timer.pause()

    def on_resize(self, event: events.Resize) -> None:
        layout = apply_layout(self, event.size.width)
        self._sync_navigation(layout)

    def action_focus_command(self) -> None:
        try:
            self.command_bar.input.focus()
        except Exception:
            pass

    def action_cycle_alert_category(self) -> None:
        """Cycle the sidebar alert section to the next category."""
        try:
            cat = self.sidebar.next_alert_category()
            self.set_status(f"Alerts: {cat}")
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

    def action_tab_prev(self) -> None:
        key = self.tab_carousel.select_prev()
        if key:
            self._switch_tab(key)

    def action_tab_next(self) -> None:
        key = self.tab_carousel.select_next()
        if key:
            self._switch_tab(key)

    def action_tab_index(self, index: str) -> None:
        tabs = getattr(self.tab_carousel, "_tabs", [])
        if not tabs:
            return
        try:
            value = int(index)
        except Exception:
            return
        idx = max(0, min(value - 1, len(tabs) - 1))
        key = tabs[idx].key
        self._switch_tab(key)

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
        entries.append(SidebarEntry(key="research", label="Research", short="R"))
        entries.append(SidebarEntry(key="ops", label="Ops", short="O"))

        active_key = self.command_context
        if active_key not in {entry.key for entry in entries}:
            active_key = "home"
        self.sidebar.set_entries(entries)
        self.sidebar.set_active(active_key)
        compact = layout in {"layout-narrow", "layout-compact"}
        self.sidebar.set_compact(compact)
        hidden = bool(getattr(self.app, "sidebar_hidden", False))
        self.sidebar.display = not hidden

        tabs = [
            TabItem(key=entry.key, label=entry.label, short=entry.short)
            for entry in entries
        ]
        self.tabbar.set_tabs(tabs)
        self.tabbar.set_active(active_key)
        self.tabbar.display = compact
        screen_id = self.id or active_key
        self._sync_tab_carousel(screen_id)
        self._sync_breadcrumb(screen_id)

    def _wire_alert_store(self) -> None:
        """Connect the app's live AlertStore into the sidebar alert section."""
        try:
            store = self.app.alert_store
            self.sidebar.set_alert_store(store)
        except Exception:
            pass

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
        if self.command_context in {"home", "views", "settings", "research", "ops"}:
            return self.app.session_state.active_profile
        return self.command_context

    def _switch_tab(self, key: str) -> None:
        handler = getattr(self.app, "switch_to_screen_id", None)
        if handler:
            handler(key)

    def _sync_tab_carousel(self, active_key: str) -> None:
        getter = getattr(self.app, "get_open_screens", None)
        if not getter:
            return
        tabs = []
        for idx, entry in enumerate(getter(), start=1):
            tabs.append(
                TabEntry(
                    key=entry["key"],
                    label=entry["label"],
                    shortcut=str(idx),
                )
            )
        self.tab_carousel.set_tabs(tabs)
        self.tab_carousel.set_active(active_key)

    def _sync_breadcrumb(self, active_key: str) -> None:
        label = None
        getter = getattr(self.app, "get_open_screens", None)
        if getter:
            for entry in getter():
                if entry["key"] == active_key:
                    label = entry["label"]
                    break
        if active_key == "home":
            breadcrumb = "home"
        elif active_key == "settings":
            breadcrumb = "home > settings"
        elif active_key == "research":
            breadcrumb = "home > research"
        elif active_key.startswith("view_"):
            breadcrumb = f"home > view/{active_key.replace('view_', '')}"
        elif active_key.startswith("profile_"):
            breadcrumb = f"home > profile/{active_key.replace('profile_', '')}"
        elif label:
            breadcrumb = f"home > {label}"
        else:
            breadcrumb = f"home > {active_key}"
        self.status.set_breadcrumb(breadcrumb)

    def _start_status_timer(self) -> None:
        self._update_status_health()
        if self._status_timer is None:
            self._status_timer = self.set_interval(1.0, self._update_status_health)
        else:
            self._status_timer.resume()

    def _update_status_health(self) -> None:
        getter = getattr(self.app, "get_status_snapshot", None)
        if not callable(getter):
            return
        try:
            snapshot = getter()
        except Exception:
            return
        self.status.set_health(snapshot)
        # Keep the sidebar alert section fresh on every tick
        try:
            self.sidebar.refresh_alerts()
        except Exception:
            pass
