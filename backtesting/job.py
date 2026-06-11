"""Minimal local job store for backtests."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Dict, Any, Callable

from .models import BacktestJobMetadata, BacktestResult


DEFAULT_ROOT = os.path.expanduser("~/.ticker_tape/jobs")
SCHEMA_NAME = "backtest_provenance"
SCHEMA_VERSION = "1.0.0"
_LEGACY_VERSION = "0.0.0"


def _parse_major(version: str) -> int:
    try:
        return int(str(version).split(".", 1)[0])
    except Exception:
        return -1


def _migrate_legacy_to_v1(payload: Dict[str, Any]) -> Dict[str, Any]:
    migrated = dict(payload)
    migrated["_schema"] = {"name": SCHEMA_NAME, "version": SCHEMA_VERSION}
    return migrated


_MIGRATIONS: Dict[str, tuple[str, Callable[[Dict[str, Any]], Dict[str, Any]]]] = {
    _LEGACY_VERSION: (SCHEMA_VERSION, _migrate_legacy_to_v1),
}


def _ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def _resolve_root(root: str | None = None) -> str:
    return str(root or DEFAULT_ROOT)


def new_run_dir(root: str | None = DEFAULT_ROOT, run_id: str | None = None) -> str:
    root = _resolve_root(root)
    run_id = run_id or uuid.uuid4().hex[:8]
    path = os.path.join(root, run_id)
    _ensure_dir(path)
    return path


def _with_schema(payload: Dict[str, Any]) -> Dict[str, Any]:
    wrapped = dict(payload)
    wrapped["_schema"] = {"name": SCHEMA_NAME, "version": SCHEMA_VERSION}
    return wrapped


def _load_with_migrations(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        raise ValueError("provenance payload must be a JSON object")
    schema = payload.get("_schema")
    if not isinstance(schema, dict):
        payload["_schema"] = {"name": SCHEMA_NAME, "version": _LEGACY_VERSION}
        schema = payload["_schema"]
    if schema.get("name") != SCHEMA_NAME:
        raise ValueError(f"unsupported schema name: {schema.get('name')}")
    version = str(schema.get("version") or _LEGACY_VERSION)
    while version != SCHEMA_VERSION:
        migration = _MIGRATIONS.get(version)
        if migration is None:
            raise ValueError(
                f"unsupported provenance schema version '{version}'. "
                "Add an explicit migration in backtesting/job.py."
            )
        next_version, migrator = migration
        payload = migrator(payload)
        payload["_schema"] = {"name": SCHEMA_NAME, "version": next_version}
        version = next_version
    if _parse_major(version) != _parse_major(SCHEMA_VERSION):
        raise ValueError(
            f"unsupported provenance schema major '{version}'. "
            "Add migration support before reading this payload."
        )
    return payload


def write_metadata(
    metadata: BacktestJobMetadata, root: str | None = DEFAULT_ROOT
) -> str:
    path = new_run_dir(root, metadata.run_id)
    meta_path = os.path.join(path, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(_with_schema(metadata.to_dict()), fh, indent=2, sort_keys=True)
    return meta_path


def write_result(result: BacktestResult, root: str | None = DEFAULT_ROOT) -> str:
    path = new_run_dir(root, result.run_id)
    result_path = os.path.join(path, "result.json")
    with open(result_path, "w", encoding="utf-8") as fh:
        json.dump(
            _with_schema(result.to_dict()), fh, default=str, indent=2, sort_keys=True
        )
    return result_path


def read_metadata(run_dir: str) -> Dict[str, Any]:
    meta_path = os.path.join(run_dir, "metadata.json")
    return _load_with_migrations(meta_path)


def read_result(run_dir: str) -> Dict[str, Any]:
    result_path = os.path.join(run_dir, "result.json")
    return _load_with_migrations(result_path)
