"""Snapshot access for the TUI."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from backend.query_helpers import load_latest_snapshot
from backend.storage import DatasetRegistry, BASE_PARQUET_ROOT


def get_latest_snapshot(
    registry: DatasetRegistry, dataset: str, timeframe: str
) -> Optional[Dict[str, Any]]:
    return load_latest_snapshot(registry, dataset, timeframe)


def get_latest_snapshot_with_path(
    registry: DatasetRegistry, dataset: str, timeframe: str
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    snapshot = load_latest_snapshot(registry, dataset, timeframe)
    ds = registry.list_datasets().get(dataset, {})
    parts = ds.get("partitions", [])
    candidates = [p for p in parts if f"timeframe={timeframe}" in p]
    if not candidates:
        return snapshot, None
    latest = max(candidates)
    return snapshot, str(BASE_PARQUET_ROOT / latest)
