"""Rich rendering helpers for theme palettes."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List, Tuple

from rich.text import Text

from tui.themes.palettes import Palette


def build_text(lines: Iterable[Tuple[str, str | None]]) -> Text:
    text = Text()
    for idx, (line, style) in enumerate(lines):
        if idx:
            text.append("\n")
        if style:
            text.append(line, style=style)
        else:
            text.append(line)
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
    if status == "error":
        return palette.accent.red
    if status == "disconnected":
        return palette.accent.orange
    if status == "empty":
        return palette.text.muted
    return palette.accent.cyan


def status_line(status: str, palette: Palette) -> Tuple[str, str]:
    return (f"Status: {format_status_label(status)}", f"bold {status_style(status, palette)}")


def heading_line(label: str, palette: Palette) -> Tuple[str, str]:
    return (label, f"bold {palette.accent.cyan}")


def muted_line(label: str, palette: Palette) -> Tuple[str, str]:
    return (label, palette.text.muted)


def format_last_good(ts_ms: int | None) -> str:
    if not ts_ms:
        return "none"
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def error_footer(error: str, updated_ts_ms: int | None, backoff_note: str, palette: Palette) -> List[Tuple[str, str]]:
    return [
        ("Feed Error", f"bold {palette.accent.red}"),
        status_line("error", palette),
        (f"Error: {error}", palette.text.primary),
        (f"Backoff: {backoff_note}", palette.text.muted),
        (f"Last good: {format_last_good(updated_ts_ms)}", palette.text.muted),
    ]
