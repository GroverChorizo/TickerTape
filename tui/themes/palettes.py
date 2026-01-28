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
    bg=BackgroundPalette(primary="#0b0b0f", panel="#111219"),
    text=TextPalette(primary="#e4e6eb", muted="#8a8f98"),
    border=BorderPalette(panel="#d946ef", focus="#a855f7"),
    accent=AccentPalette(
        cyan="#7dd3fc",
        purple="#d946ef",
        green="#39ff88",
        orange="#f59e0b",
        red="#ef4444",
    ),
)

dark_pro = Palette(
    theme_id="dark_pro",
    name="Dark Pro",
    bg=BackgroundPalette(primary="#0f1016", panel="#161826"),
    text=TextPalette(primary="#e3e6ed", muted="#949aa6"),
    border=BorderPalette(panel="#c026d3", focus="#9333ea"),
    accent=AccentPalette(
        cyan="#7dd3fc",
        purple="#c026d3",
        green="#22c55e",
        orange="#f59e0b",
        red="#ef4444",
    ),
)

matrix = Palette(
    theme_id="matrix",
    name="Matrix",
    bg=BackgroundPalette(primary="#050607", panel="#0b0c0f"),
    text=TextPalette(primary="#cfe6d4", muted="#6f7c72"),
    border=BorderPalette(panel="#a855f7", focus="#d946ef"),
    accent=AccentPalette(
        cyan="#7dd3fc",
        purple="#a855f7",
        green="#22c55e",
        orange="#f59e0b",
        red="#ef4444",
    ),
)

minimal = Palette(
    theme_id="minimal",
    name="Minimal",
    bg=BackgroundPalette(primary="#111217", panel="#171822"),
    text=TextPalette(primary="#e6e8ee", muted="#9aa0ac"),
    border=BorderPalette(panel="#d946ef", focus="#a855f7"),
    accent=AccentPalette(
        cyan="#7dd3fc",
        purple="#d946ef",
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
