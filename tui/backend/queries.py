"""Query helpers used by the TUI."""
from __future__ import annotations

from typing import Any, Dict, List

from backend.query_helpers import list_datasets, query_recent_events
from backend.storage import DatasetRegistry


def list_registry_datasets(registry: DatasetRegistry) -> Dict[str, Any]:
    return list_datasets(registry)


def recent_events(registry: DatasetRegistry, dataset: str, since_ts_ms: int) -> List[Dict[str, Any]]:
    return query_recent_events(registry, dataset, since_ts_ms)
