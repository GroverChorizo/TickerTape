"""Backend registry access for the TUI."""
from __future__ import annotations

from backend.storage import DatasetRegistry


def get_registry() -> DatasetRegistry:
    return DatasetRegistry()
