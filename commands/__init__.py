"""Command package scaffolding."""

from .parser import CommandSpec, OptionSpec, parse_command
from .registry import Command, CommandRegistry, Handler

__all__ = [
    "Command",
    "CommandRegistry",
    "CommandSpec",
    "Handler",
    "OptionSpec",
    "parse_command",
]
