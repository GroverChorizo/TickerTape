"""Lightweight JSON cache for last snapshots and preferences."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json


CACHE_PATH = Path("data/ui_cache.json")


def load_cache() -> Dict[str, Any]:
    if not CACHE_PATH.exists():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_cache(payload: Dict[str, Any]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
