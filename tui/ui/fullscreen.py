"""Fullscreen toggle helpers."""

from __future__ import annotations

from tui.state.session import get_profile_state, save_session_state


def apply_fullscreen_state(app, screen, profile: str) -> bool:
    state = get_profile_state(app.session_state, profile)
    _apply_screen_class(screen, "fullscreen", state.fullscreen)
    return state.fullscreen


def toggle_fullscreen(app, screen, profile: str) -> bool:
    state = get_profile_state(app.session_state, profile)
    state.fullscreen = not state.fullscreen
    save_session_state(app.session_state)
    _apply_screen_class(screen, "fullscreen", state.fullscreen)
    return state.fullscreen


def _apply_screen_class(screen, class_name: str, enabled: bool) -> None:
    try:
        if enabled:
            screen.add_class(class_name)
        else:
            screen.remove_class(class_name)
    except Exception:
        pass
