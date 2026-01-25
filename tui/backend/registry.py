"""Backend registry access for the TUI."""
from __future__ import annotations

from backend.storage import DatasetRegistry

from ..config import load_config


def get_registry() -> DatasetRegistry:
    config = load_config()
    registry_path = config.data_root / "_registry.json"
    return DatasetRegistry(path=registry_path)
