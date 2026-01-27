"""Command parsing utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import shlex


@dataclass(frozen=True)
class OptionSpec:
    name: str
    short: Optional[str] = None
    takes_value: bool = True
    required: bool = False
    default: Any = None


@dataclass(frozen=True)
class CommandSpec:
    name: str
    options: List[OptionSpec]
    min_args: int = 0
    max_args: Optional[int] = None


@dataclass(frozen=True)
class ParseResult:
    ok: bool
    command: Optional[str] = None
    args: Optional[List[str]] = None
    options: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


def parse_command(spec: CommandSpec, raw: str) -> ParseResult:
    """Parse a command string against the provided spec."""
    try:
        tokens = shlex.split(raw or "")
    except ValueError as exc:
        return ParseResult(ok=False, error=f"Parse error: {exc}")
    if not tokens:
        return ParseResult(ok=False, error="Empty command.")
    if tokens[0] != spec.name:
        return ParseResult(ok=False, error=f"Unknown command: {tokens[0]}")

    options: Dict[str, Any] = {opt.name: opt.default for opt in spec.options}
    option_map = {f"--{opt.name}": opt for opt in spec.options}
    short_map = {f"-{opt.short}": opt for opt in spec.options if opt.short}

    args: List[str] = []
    it = iter(tokens[1:])
    for token in it:
        if token == "--":
            args.extend(list(it))
            break
        if token.startswith("--"):
            opt = option_map.get(token)
            if not opt:
                return ParseResult(ok=False, error=f"Unknown option: {token}")
            if opt.takes_value:
                try:
                    value = next(it)
                except StopIteration:
                    return ParseResult(ok=False, error=f"Missing value for {token}")
                options[opt.name] = value
            else:
                options[opt.name] = True
            continue
        if token.startswith("-") and token != "-":
            opt = short_map.get(token)
            if not opt:
                return ParseResult(ok=False, error=f"Unknown option: {token}")
            if opt.takes_value:
                try:
                    value = next(it)
                except StopIteration:
                    return ParseResult(ok=False, error=f"Missing value for {token}")
                options[opt.name] = value
            else:
                options[opt.name] = True
            continue
        args.append(token)

    for opt in spec.options:
        if opt.required and (options.get(opt.name) in (None, "")):
            return ParseResult(ok=False, error=f"Missing required option: --{opt.name}")

    if len(args) < spec.min_args:
        return ParseResult(ok=False, error="Missing required arguments.")
    if spec.max_args is not None and len(args) > spec.max_args:
        return ParseResult(ok=False, error="Too many arguments.")

    return ParseResult(ok=True, command=spec.name, args=args, options=options)
