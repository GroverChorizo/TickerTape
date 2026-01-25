"""Diagnostics collection for the TUI."""
from __future__ import annotations

from dataclasses import asdict
from importlib import metadata
from pathlib import Path
from typing import Dict, Any
import platform
import sys

from backend.storage import DatasetRegistry

from .config import TuiConfig


def _version(pkg: str) -> str:
    try:
        return metadata.version(pkg)
    except Exception:
        return "unknown"


def collect_diagnostics(config: TuiConfig, registry: DatasetRegistry) -> Dict[str, Any]:
    datasets = registry.list_datasets()
    dataset_counts = {name: len(meta.get("partitions", [])) for name, meta in datasets.items()}
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "textual": _version("textual"),
        "rich": _version("rich"),
        "data_root": str(config.data_root),
        "config_path": str(config.config_path),
        "mode": config.mode,
        "profile": config.profile,
        "secrets_path": str(config.secrets_path) if config.secrets_path else None,
        "registry_exists": (config.data_root / "_registry.json").exists(),
        "dataset_counts": dataset_counts,
    }
