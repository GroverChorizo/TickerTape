"""Minimal theme tokens."""
from __future__ import annotations

from .base import Theme, ThemeTokens

THEME = Theme(
    theme_id="minimal",
    name="Minimal",
    tokens=ThemeTokens(
        background_primary="#101317",
        panel_background="#141a22",
        panel_border="#2b3543",
        text_primary="#e5e7eb",
        text_secondary="#a1a9b4",
        accent_header="#93c5fd",
        accent_whale="#93c5fd",
        success="#16a34a",
        warning="#f59e0b",
        critical="#ef4444",
        info="#60a5fa",
        focus_border="#93c5fd",
    ),
)
