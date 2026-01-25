"""Dark Pro theme tokens."""
from __future__ import annotations

from .base import Theme, ThemeTokens

THEME = Theme(
    theme_id="dark_pro",
    name="Dark Pro",
    tokens=ThemeTokens(
        background_primary="#0b0f14",
        panel_background="#0f172a",
        panel_border="#1f2937",
        text_primary="#dbe4ee",
        text_secondary="#94a3b8",
        accent_header="#7dd3fc",
        accent_whale="#7dd3fc",
        success="#22c55e",
        warning="#f59e0b",
        critical="#ef4444",
        info="#60a5fa",
        focus_border="#7dd3fc",
    ),
)
