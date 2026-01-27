"""Theme manager persistence per profile using session state."""

from __future__ import annotations

from typing import Optional

from .palettes import DEFAULT_THEME_ID, Palette, get_palette, list_palettes
from tui.state.session import (
    ProfileState,
    SessionState,
    load_session_state,
    save_session_state,
)


class ThemeManager:
    def __init__(self, session_state: Optional[SessionState] = None) -> None:
        self._session_state = session_state or load_session_state()
        self._active_profile = self._session_state.active_profile

    def available(self) -> list[str]:
        return [palette.theme_id for palette in list_palettes()]

    def get(self, theme_name: str) -> Palette:
        return get_palette(theme_name)

    def current(self) -> Palette:
        return self.get(self.current_id())

    def current_id(self) -> str:
        state = self._profile_state()
        return state.theme or DEFAULT_THEME_ID

    def apply(self, app, theme_name: str) -> None:
        palette = self.get(theme_name)
        state = self._profile_state()
        state.theme = palette.theme_id
        save_session_state(self._session_state)
        if hasattr(app, "apply_palette"):
            app.apply_palette(palette)

    def color(self, key: str) -> str:
        palette = self.current()
        return palette.to_tokens().get(key, "")

    def set_active_profile(self, profile: str) -> None:
        self._active_profile = profile

    def _profile_state(self) -> ProfileState:
        if self._active_profile not in self._session_state.profiles:
            self._session_state.profiles[self._active_profile] = ProfileState()
        return self._session_state.profiles[self._active_profile]
