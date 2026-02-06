"""Lightweight JSON cache for last snapshots and preferences."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json
import os


DEFAULT_CACHE_PATH = Path("data/ui_cache.json")
_CACHE_PATH_ENV = os.environ.get("TICKERTAPE_CACHE_PATH")
CACHE_PATH = Path(_CACHE_PATH_ENV) if _CACHE_PATH_ENV else DEFAULT_CACHE_PATH


def load_cache() -> Dict[str, Any]:
    if os.environ.get("TICKERTAPE_DISABLE_CACHE") == "1":
        return {}
    if not CACHE_PATH.exists():
        return {}
    try:
        payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        # Keep tests deterministic by ignoring persisted sidebar state.
        if os.environ.get("PYTEST_CURRENT_TEST"):
            payload.pop("sidebar_hidden", None)
        return payload
    except Exception:
        return {}


def save_cache(payload: Dict[str, Any]) -> None:
    if os.environ.get("TICKERTAPE_DISABLE_CACHE") == "1":
        return
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
