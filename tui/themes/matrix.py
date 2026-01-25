"""Matrix theme tokens."""
from __future__ import annotations

from .base import Theme, ThemeTokens

THEME = Theme(
    theme_id="matrix",
    name="Matrix",
    tokens=ThemeTokens(
        background_primary="#050707",
        panel_background="#0b0f0b",
        panel_border="#1f3b2f",
        text_primary="#b7f7c5",
        text_secondary="#5b8a6a",
        accent_header="#7ef2a0",
        accent_whale="#7ef2a0",
        success="#22c55e",
        warning="#f59e0b",
        critical="#ef4444",
        info="#38bdf8",
        focus_border="#7ef2a0",
    ),
)
