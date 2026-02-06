"""Command helpers for diagnostics."""

from __future__ import annotations

from typing import Any, Dict

from providers.base import Provider
from providers.diagnostics import diagnose_provider


def diagnose_command(provider: Provider) -> str:
    """Return a short diagnostics string for CLI/TUI."""
    report = diagnose_provider(provider)
    http = report.get("http", "unknown")
    ws = report.get("ws", "unknown")
    latency = report.get("latency_ms", "n/a")
    last_update = report.get("last_update_ms")
    suffix = f" | last_update_ms={last_update}" if last_update is not None else ""
    return f"Diagnostics: http={http} | ws={ws} | latency_ms={latency}{suffix}"


def diagnostics_payload(provider: Provider) -> Dict[str, Any]:
    """Return the raw report for structured use."""
    return diagnose_provider(provider)
