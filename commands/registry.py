"""Command registry for global commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional


Handler = Callable[[str, list[str]], Optional[str]]


@dataclass(frozen=True)
class Command:
    name: str
    description: str
    handler: Handler
    aliases: list[str]
    contexts: list[str]


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
        for key in [cmd.name, *cmd.aliases]:
            self._commands[key] = cmd

    def match(self, name: str) -> Optional[Command]:
        return self._commands.get(name)

    def names(self) -> list[str]:
        return sorted({cmd.name for cmd in self._commands.values()})

    def help_for(self, context: str) -> List[str]:
        lines: List[str] = []
        for cmd in {c.name: c for c in self._commands.values()}.values():
            if cmd.contexts and context not in cmd.contexts:
                continue
            lines.append(f"{cmd.name:<12} - {cmd.description}")
        return sorted(lines)
