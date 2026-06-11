#!/usr/bin/env python3
"""TickerTape release gate — runs all quality gates in sequence.

Usage:
    python tools/release_gate.py

Exits 0 when all gates pass, 1 on any failure.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _header(msg: str) -> None:
    print(f"\n{_BOLD}{_YELLOW}▶ {msg}{_RESET}")


def _ok(msg: str) -> None:
    print(f"{_GREEN}✓ {msg}{_RESET}")


def _fail(msg: str) -> None:
    print(f"{_RED}✗ {msg}{_RESET}", file=sys.stderr)


def _run_gate(label: str, cmd: list[str]) -> bool:
    _header(label)
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode == 0:
        _ok(f"{label} passed")
        return True
    _fail(f"{label} FAILED (exit code {result.returncode})")
    return False


def main() -> int:
    gates: list[tuple[str, list[str]]] = [
        ("pytest", [sys.executable, "-m", "pytest", "-q"]),
        ("ruff", [sys.executable, "-m", "ruff", "check", "."]),
        ("mypy", [sys.executable, "-m", "mypy", "."]),
        (
            "data integrity gate",
            [sys.executable, "tools/data_integrity_gate.py", "--root", "."],
        ),
    ]
    failed: list[str] = []
    for label, cmd in gates:
        if not _run_gate(label, cmd):
            failed.append(label)
        print()

    if not failed:
        print(f"{_BOLD}{_GREEN}✓ All gates passed.{_RESET}")
        return 0

    print(
        f"{_BOLD}{_RED}✗ {len(failed)} gate(s) failed: {', '.join(failed)}{_RESET}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
