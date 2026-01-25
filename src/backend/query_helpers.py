"""Lightweight helpers for frontend to query datasets and snapshots.

- list_datasets: return registry listing
- load_latest_snapshot: find latest partition for feed/timeframe and read parquet or ndjson
- query_recent_events: naive read of events partition files within time window
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pathlib import Path
import json
import logging

from . import storage
from .storage import DatasetRegistry  # for type convenience

logger = logging.getLogger(__name__)


def list_datasets(registry: DatasetRegistry) -> Dict[str, Any]:
    return registry.list_datasets()


def _read_parquet_or_ndjson(path: Path) -> List[Dict[str, Any]]:
    # If the path itself is an ndjson file, read it directly
    if path.name.endswith(".ndjson") or path.suffix == ".ndjson":
        out = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                out.append(json.loads(line))
        return out

    try:
        import pyarrow.parquet as pq
        tbl = pq.read_table(str(path))
        data = [dict(row) for row in tbl.to_pylist()]
        return data
    except Exception:
        # fallback to ndjson sidecar (e.g., part-<ts>.parquet.ndjson)
        nd = path.with_suffix(path.suffix + ".ndjson")
        if nd.exists():
            out = []
            with nd.open("r", encoding="utf-8") as f:
                for line in f:
                    out.append(json.loads(line))
            return out
        raise


def load_latest_snapshot(registry: DatasetRegistry, dataset_name: str, timeframe: str) -> Optional[Dict[str, Any]]:
    ds = registry.list_datasets().get(dataset_name)
    if not ds:
        return None
    parts = ds.get("partitions", [])
    # find partitions that match timeframe
    candidates = [p for p in parts if f"timeframe={timeframe}" in p]
    if not candidates:
        return None
    # pick latest by lexicographic of filename (we use part-<ts>.parquet)
    latest = max(candidates)
    path = storage.BASE_PARQUET_ROOT / latest
    # Consider NDJSON variant (.parquet.ndjson)
    candidates = [path, path.with_suffix(path.suffix + ".ndjson")]

    # fallback: if partition was registered without feed prefix, try joining with dataset_name
    alt = storage.BASE_PARQUET_ROOT / dataset_name / latest
    candidates.extend([alt, alt.with_suffix(alt.suffix + ".ndjson")])

    path_to_use = None
    for p in candidates:
        if p.exists():
            path_to_use = p
            break

    if path_to_use is None:
        logger.error({"event": "read_snapshot_not_found", "path": str(path)})
        return None

    try:
        rows = _read_parquet_or_ndjson(path_to_use)
        return rows[-1] if rows else None
    except Exception as e:
        logger.error({"event": "read_snapshot_failed", "err": str(e), "path": str(path_to_use)})
        return None


def query_recent_events(registry: DatasetRegistry, dataset_name: str, since_ts_ms: int) -> List[Dict[str, Any]]:
    ds = registry.list_datasets().get(dataset_name)
    if not ds:
        return []
    parts = ds.get("partitions", [])
    out = []
    for p in parts:
        path = storage.BASE_PARQUET_ROOT / p
        try:
            rows = _read_parquet_or_ndjson(path)
        except Exception:
            continue
        for r in rows:
            # event-like rows may have timestamp fields
            ts = r.get("window_start_ts_ms") or r.get("timestamp_ms") or r.get("timestamp")
            if ts is None:
                out.append(r)
                continue
            try:
                t = int(ts)
            except Exception:
                continue
            if t >= since_ts_ms:
                out.append(r)
    return out
