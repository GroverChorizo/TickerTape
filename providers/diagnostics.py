"""Diagnostics helpers for providers."""

from __future__ import annotations

from typing import Any, Dict
import time

from .base import Provider


def diagnose_provider(provider: Provider) -> Dict[str, Any]:
    """Return a diagnostics report with latency measurements."""
    start = time.perf_counter()
    report = provider.diagnostics() or {}
    elapsed_ms = (time.perf_counter() - start) * 1000
    if "http" not in report:
        report["http"] = "unknown"
    if "ws" not in report:
        report["ws"] = "unknown"
    report["latency_ms"] = round(elapsed_ms, 2)
    return report
