"""Theme definitions for the TickerTape TUI."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ThemeTokens:
    background_primary: str
    panel_background: str
    panel_border: str
    text_primary: str
    text_secondary: str
    accent_header: str
    accent_whale: str
    success: str
    warning: str
    critical: str
    info: str
    focus_border: str

    def to_css_variables(self) -> Dict[str, str]:
        return {
            "background-primary": self.background_primary,
            "panel-background": self.panel_background,
            "panel-border": self.panel_border,
            "text-primary": self.text_primary,
            "text-secondary": self.text_secondary,
            "accent-header": self.accent_header,
            "accent-whale": self.accent_whale,
            "alert-success": self.success,
            "alert-warning": self.warning,
            "alert-critical": self.critical,
            "alert-info": self.info,
            "focus-border": self.focus_border,
        }


@dataclass(frozen=True)
class Theme:
    theme_id: str
    name: str
    tokens: ThemeTokens

    def to_css_variables(self) -> Dict[str, str]:
        return self.tokens.to_css_variables()
