"""Snapshot access for the TUI."""
from __future__ import annotations

from typing import Any, Dict, Optional

from backend.query_helpers import load_latest_snapshot
from backend.storage import DatasetRegistry


def get_latest_snapshot(registry: DatasetRegistry, dataset: str, timeframe: str) -> Optional[Dict[str, Any]]:
    return load_latest_snapshot(registry, dataset, timeframe)
