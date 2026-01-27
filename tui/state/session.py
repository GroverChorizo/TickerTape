"""Local session persistence for profile/layout state."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List
import json

from .profiles import DEFAULT_PANEL_ORDER, default_profile


STATE_PATH = Path("data/tui_state.json")


@dataclass
class ProfileState:
    panel_order: List[str] = field(default_factory=lambda: list(DEFAULT_PANEL_ORDER))
    collapsed: Dict[str, bool] = field(default_factory=dict)
    theme: str = ""
    selected_symbol: str | None = None
    fullscreen: bool = False
    density: str = "comfortable"


@dataclass
class SessionState:
    active_profile: str
    profiles: Dict[str, ProfileState]

    def to_dict(self) -> Dict:
        return {
            "active_profile": self.active_profile,
            "profiles": {
                name: {
                    "panel_order": state.panel_order,
                    "collapsed": state.collapsed,
                    "theme": state.theme,
                    "selected_symbol": state.selected_symbol,
                    "fullscreen": state.fullscreen,
                    "density": state.density,
                }
                for name, state in self.profiles.items()
            },
        }

    @classmethod
    def from_dict(cls, payload: Dict) -> "SessionState":
        profiles: Dict[str, ProfileState] = {}
        for name, state in payload.get("profiles", {}).items():
            profiles[name] = ProfileState(
                panel_order=list(state.get("panel_order", DEFAULT_PANEL_ORDER)),
                collapsed=dict(state.get("collapsed", {})),
                theme=state.get("theme", ""),
                selected_symbol=state.get("selected_symbol"),
                fullscreen=bool(state.get("fullscreen", False)),
                density=state.get("density", "comfortable"),
            )
        active_profile = payload.get("active_profile", default_profile().name)
        return cls(active_profile=active_profile, profiles=profiles)


def _ensure_state_dir() -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_session_state() -> SessionState:
    _ensure_state_dir()
    if not STATE_PATH.exists():
        return SessionState(active_profile=default_profile().name, profiles={})
    payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return SessionState.from_dict(payload)


def save_session_state(state: SessionState) -> None:
    _ensure_state_dir()
    STATE_PATH.write_text(
        json.dumps(state.to_dict(), indent=2, sort_keys=True), encoding="utf-8"
    )


def get_profile_state(state: SessionState, profile_name: str) -> ProfileState:
    if profile_name not in state.profiles:
        from .profiles import PROFILES

        default_order = (
            PROFILES.get(profile_name).default_panel_order
            if profile_name in PROFILES
            else DEFAULT_PANEL_ORDER
        )
        state.profiles[profile_name] = ProfileState(panel_order=list(default_order))
    return state.profiles[profile_name]
