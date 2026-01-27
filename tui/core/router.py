"""Route parsing for TickerTape screens."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Route:
    kind: str
    name: Optional[str] = None


def parse_route(raw: str) -> Route:
    text = (raw or "").strip()
    if text in {"", "/", "home"}:
        return Route("home")
    if text.startswith("/"):
        text = text[1:]
    if text.startswith("profiles/"):
        return Route("profile", text.split("/", 1)[1])
    if text.startswith("profile/"):
        return Route("profile", text.split("/", 1)[1])
    if text.startswith("views/"):
        return Route("view", text.split("/", 1)[1])
    if text.startswith("view/"):
        return Route("view", text.split("/", 1)[1])
    return Route("unknown", text)
