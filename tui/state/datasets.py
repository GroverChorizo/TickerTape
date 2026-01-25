"""Dataset registry helpers for the TUI."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set
import re

from backend.storage import DatasetRegistry


TIMEFRAME_PATTERN = re.compile(r"timeframe=([^/\\\\]+)")


@dataclass
class DatasetInfo:
    name: str
    timeframes: List[str]


def _extract_timeframes(partitions: List[str]) -> Set[str]:
    timeframes: Set[str] = set()
    for part in partitions:
        match = TIMEFRAME_PATTERN.search(part)
        if match:
            timeframes.add(match.group(1))
    return timeframes


def load_datasets(registry: DatasetRegistry) -> Dict[str, DatasetInfo]:
    datasets = registry.list_datasets()
    out: Dict[str, DatasetInfo] = {}
    for name, meta in datasets.items():
        partitions = meta.get("partitions", [])
        timeframes = sorted(_extract_timeframes(partitions))
        out[name] = DatasetInfo(name=name, timeframes=timeframes)
    return out


def dataset_timeframes(datasets: Dict[str, DatasetInfo], dataset_name: str) -> List[str]:
    info = datasets.get(dataset_name)
    if not info:
        return []
    return info.timeframes


def latest_timeframe(datasets: Dict[str, DatasetInfo], dataset_name: str) -> Optional[str]:
    info = datasets.get(dataset_name)
    if not info or not info.timeframes:
        return None
    return info.timeframes[-1]
