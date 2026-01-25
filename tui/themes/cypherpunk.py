"""Cypherpunk theme tokens."""
from __future__ import annotations

from .base import Theme, ThemeTokens

THEME = Theme(
    theme_id="cypherpunk",
    name="Cypherpunk",
    tokens=ThemeTokens(
        background_primary="#0a0e1a",
        panel_background="#0d1117",
        panel_border="#243044",
        text_primary="#d6dde6",
        text_secondary="#7a8797",
        accent_header="#79b4c4",
        accent_whale="#79b4c4",
        success="#39ff88",
        warning="#f59e0b",
        critical="#ef4444",
        info="#60a5fa",
        focus_border="#79b4c4",
    ),
)
