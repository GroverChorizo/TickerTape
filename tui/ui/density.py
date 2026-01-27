"""Density toggle helpers."""

from __future__ import annotations

from tui.state.session import get_profile_state, save_session_state


def apply_density_state(app, screen, profile: str) -> str:
    state = get_profile_state(app.session_state, profile)
    _apply_density_class(screen, state.density)
    return state.density


def toggle_density(app, screen, profile: str) -> str:
    state = get_profile_state(app.session_state, profile)
    state.density = "compact" if state.density != "compact" else "comfortable"
    save_session_state(app.session_state)
    _apply_density_class(screen, state.density)
    return state.density


def _apply_density_class(screen, density: str) -> None:
    for name in ("density-compact", "density-comfortable"):
        try:
            screen.remove_class(name)
        except Exception:
            pass
    class_name = f"density-{density}"
    try:
        screen.add_class(class_name)
    except Exception:
        pass
