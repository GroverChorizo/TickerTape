"""Theme manager persistence per profile."""
from __future__ import annotations

from pathlib import Path
from typing import Dict
import json

from .palettes import DEFAULT_THEME_ID, get_palette, list_palettes, Palette

THEME_STATE_PATH = Path("data/theme_state.json")


def _ensure_theme_state_dir() -> None:
    THEME_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_state() -> Dict[str, str]:
    _ensure_theme_state_dir()
    if not THEME_STATE_PATH.exists():
        return {}
    return json.loads(THEME_STATE_PATH.read_text(encoding="utf-8"))


def _save_state(state: Dict[str, str]) -> None:
    _ensure_theme_state_dir()
    THEME_STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def list_theme_ids() -> list[str]:
    return [palette.theme_id for palette in list_palettes()]


def get_theme_for_profile(profile: str) -> str:
    state = _load_state()
    return state.get(profile, DEFAULT_THEME_ID)


def set_theme_for_profile(profile: str, theme_id: str) -> str:
    palette = get_palette(theme_id)
    state = _load_state()
    state[profile] = palette.theme_id
    _save_state(state)
    return palette.theme_id


def get_palette_for_profile(profile: str) -> Palette:
    theme_id = get_theme_for_profile(profile)
    return get_palette(theme_id)
