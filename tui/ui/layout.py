"""Layout manager with breakpoint classes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class LayoutBreakpoints:
    ultra: int = 160
    wide: int = 120
    standard: int = 100
    narrow: int = 80


BREAKPOINTS = LayoutBreakpoints()


def layout_class(width: int) -> str:
    if width >= BREAKPOINTS.ultra:
        return "layout-ultra"
    if width >= BREAKPOINTS.wide:
        return "layout-wide"
    if width >= BREAKPOINTS.standard:
        return "layout-standard"
    if width >= BREAKPOINTS.narrow:
        return "layout-narrow"
    return "layout-compact"


def apply_layout(screen, width: int) -> str:
    """Apply layout class to the screen and return the class name."""
    current = layout_class(width)
    _set_layout_class(screen, current)
    return current


def apply_panel_sizes(panels: Iterable, sizes: dict[str, dict[str, int]]) -> None:
    for panel in panels:
        panel_id = getattr(panel, "panel_id", "")
        if not panel_id or panel_id not in sizes:
            continue
        size = sizes[panel_id]
        width = size.get("width")
        height = size.get("height")
        if hasattr(panel, "resize_to") and width and height:
            panel.resize_to(int(width), int(height))


def _set_layout_class(screen, current: str) -> None:
    classes: Iterable[str] = getattr(screen, "classes", [])
    existing = [c for c in classes if c.startswith("layout-")]
    for name in existing:
        try:
            screen.remove_class(name)
        except Exception:
            pass
    try:
        screen.add_class(current)
    except Exception:
        pass
