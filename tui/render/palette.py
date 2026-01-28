"""Rich rendering helpers for theme palettes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List, Tuple, Union

from rich.text import Text

from tui.themes.palettes import Palette


RenderableLine = Union[Tuple[str, str | None], Text]


def build_text(lines: Iterable[RenderableLine]) -> Text:
    text = Text()
    for idx, line in enumerate(lines):
        if idx:
            text.append("\n")
        if isinstance(line, Text):
            text.append(line)
        else:
            line_text, style = line
            if style:
                text.append(line_text, style=style)
            else:
                text.append(line_text)
    return text


def format_status_label(status: str) -> str:
    labels = {
        "ok": "LIVE",
        "loading": "LOADING",
        "empty": "NO DATA",
        "error": "ERROR",
        "disconnected": "DISCONNECTED",
    }
    return labels.get(status, status.upper())


def status_style(status: str, palette: Palette) -> str:
    if status == "ok":
        return palette.accent.green
    if status == "live":
        return palette.accent.green
    if status == "loading":
        return palette.accent.purple
    if status == "disconnected":
        return palette.accent.orange
    if status == "stale":
        return palette.accent.orange
    if status == "error":
        return palette.accent.orange
    if status == "empty":
        return palette.text.muted
    return palette.text.primary


def status_line(status: str, palette: Palette) -> Tuple[str, str]:
    return (
        f"Status: {format_status_label(status)}",
        f"bold {status_style(status, palette)}",
    )


def heading_line(label: str, palette: Palette) -> Tuple[str, str]:
    return (label, f"bold {palette.accent.purple}")


def muted_line(label: str, palette: Palette) -> Tuple[str, str]:
    return (label, palette.text.muted)


def format_last_good(ts_ms: int | None) -> str:
    if not ts_ms:
        return "none"
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def panel_header(title: str, status: str, palette: Palette) -> Text:
    header = Text()
    header.append(title, style=f"bold {palette.text.primary}")
    header.append(" ")
    header.append(
        f"[{format_status_label(status)}]",
        style=f"bold {status_style(status, palette)}",
    )
    return header


def last_updated_line(updated_ts_ms: int | None, palette: Palette) -> Tuple[str, str]:
    label = "never" if not updated_ts_ms else format_last_good(updated_ts_ms)
    return (f"Last updated: {label}", palette.text.muted)


def numeric_style_for(value: float | None, palette: Palette) -> str:
    """Return a style string for numeric sign coloring."""
    try:
        v = float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return palette.text.primary
    if v > 0:
        return f"bold {palette.accent.green}"
    if v < 0:
        return f"bold {palette.accent.red}"
    return palette.text.primary


def format_signed_percent(value: float | None) -> str:
    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "n/a"
