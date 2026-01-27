"""Command registry for TickerTape screens."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional


Handler = Callable[[str, List[str]], Optional[str]]


@dataclass(frozen=True)
class Command:
    name: str
    description: str
    handler: Handler
    aliases: List[str]
    contexts: List[str]


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: Dict[str, Command] = {}

    def register(
        self,
        name: str,
        description: str,
        handler: Handler,
        *,
        aliases: Optional[Iterable[str]] = None,
        contexts: Optional[Iterable[str]] = None,
    ) -> None:
        cmd = Command(
            name=name,
            description=description,
            handler=handler,
            aliases=list(aliases or []),
            contexts=list(contexts or []),
        )
        for key in [name, *cmd.aliases]:
            self._commands[key] = cmd

    def match(self, name: str) -> Optional[Command]:
        return self._commands.get(name)

    def help_for(self, context: str) -> List[str]:
        lines: List[str] = []
        for cmd in {c.name: c for c in self._commands.values()}.values():
            if cmd.contexts and context not in cmd.contexts:
                continue
            lines.append(f"{cmd.name:<12} - {cmd.description}")
        return sorted(lines)
