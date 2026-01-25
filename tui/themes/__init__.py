"""Theme registry for the TUI."""
from __future__ import annotations

from typing import Dict, List

from .base import Theme
from .cypherpunk import THEME as CYPHERPUNK
from .dark_pro import THEME as DARK_PRO
from .matrix import THEME as MATRIX
from .minimal import THEME as MINIMAL

THEMES: Dict[str, Theme] = {
    CYPHERPUNK.theme_id: CYPHERPUNK,
    DARK_PRO.theme_id: DARK_PRO,
    MATRIX.theme_id: MATRIX,
    MINIMAL.theme_id: MINIMAL,
}

DEFAULT_THEME_ID = CYPHERPUNK.theme_id


def list_themes() -> List[Theme]:
    return list(THEMES.values())


def get_theme(theme_id: str) -> Theme:
    return THEMES.get(theme_id, THEMES[DEFAULT_THEME_ID])
