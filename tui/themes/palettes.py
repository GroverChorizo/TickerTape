"""Semantic theme palettes for the TUI."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class BackgroundPalette:
    primary: str
    panel: str


@dataclass(frozen=True)
class TextPalette:
    primary: str
    muted: str


@dataclass(frozen=True)
class BorderPalette:
    panel: str
    focus: str


@dataclass(frozen=True)
class AccentPalette:
    cyan: str
    purple: str
    green: str
    orange: str
    red: str


@dataclass(frozen=True)
class Palette:
    theme_id: str
    name: str
    bg: BackgroundPalette
    text: TextPalette
    border: BorderPalette
    accent: AccentPalette

    def to_tokens(self) -> Dict[str, str]:
        return {
            "background_primary": self.bg.primary,
            "panel_background": self.bg.panel,
            "panel_border": self.border.panel,
            "text_primary": self.text.primary,
            "text_muted": self.text.muted,
            "accent_header": self.accent.cyan,
            "accent_focus": self.border.focus,
            "accent_ai": self.accent.purple,
            "success": self.accent.green,
            "warning": self.accent.orange,
            "danger": self.accent.red,
        }


cypherpunk_default = Palette(
    theme_id="cypherpunk",
    name="Cypherpunk",
    bg=BackgroundPalette(primary="#0a0e1a", panel="#0d1117"),
    text=TextPalette(primary="#d6dde6", muted="#7a8797"),
    border=BorderPalette(panel="#243044", focus="#79b4c4"),
    accent=AccentPalette(
        cyan="#79b4c4",
        purple="#8b5cf6",
        green="#39ff88",
        orange="#f59e0b",
        red="#ef4444",
    ),
)

dark_pro = Palette(
    theme_id="dark_pro",
    name="Dark Pro",
    bg=BackgroundPalette(primary="#0b0f14", panel="#101826"),
    text=TextPalette(primary="#d7dee7", muted="#8a96a6"),
    border=BorderPalette(panel="#2a3647", focus="#6aaed1"),
    accent=AccentPalette(
        cyan="#6aaed1",
        purple="#8b5cf6",
        green="#22c55e",
        orange="#f59e0b",
        red="#ef4444",
    ),
)

matrix = Palette(
    theme_id="matrix",
    name="Matrix",
    bg=BackgroundPalette(primary="#050707", panel="#0b0f0b"),
    text=TextPalette(primary="#b7f7c5", muted="#5b8a6a"),
    border=BorderPalette(panel="#1f3b2f", focus="#7ef2a0"),
    accent=AccentPalette(
        cyan="#7ef2a0",
        purple="#a855f7",
        green="#22c55e",
        orange="#f59e0b",
        red="#ef4444",
    ),
)

minimal = Palette(
    theme_id="minimal",
    name="Minimal",
    bg=BackgroundPalette(primary="#101317", panel="#141a22"),
    text=TextPalette(primary="#e5e7eb", muted="#a1a9b4"),
    border=BorderPalette(panel="#2b3543", focus="#93c5fd"),
    accent=AccentPalette(
        cyan="#93c5fd",
        purple="#8b5cf6",
        green="#16a34a",
        orange="#f59e0b",
        red="#ef4444",
    ),
)

PALETTES: Dict[str, Palette] = {
    cypherpunk_default.theme_id: cypherpunk_default,
    dark_pro.theme_id: dark_pro,
    matrix.theme_id: matrix,
    minimal.theme_id: minimal,
}

DEFAULT_THEME_ID = cypherpunk_default.theme_id


def list_palettes() -> List[Palette]:
    return list(PALETTES.values())


def get_palette(theme_id: str) -> Palette:
    return PALETTES.get(theme_id, cypherpunk_default)
