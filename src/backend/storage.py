"""Storage helpers: Parquet writer and DatasetRegistry.

- Writes partitioned Parquet files under data/parquet/
- Registers dataset partitions in a local JSON registry
"""
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Iterable, List
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

REGISTRY_PATH = Path("data/parquet/_registry.json")
BASE_PARQUET_ROOT = Path("data/parquet")


class DatasetRegistry:
    """Simple JSON-backed dataset registry to list datasets and partitions.

    Registry format:
    {
      "datasets": {
        "feed=liquidations_events": {
            "partitions": ["timeframe=1h/date=2026-01-01/part-000.parquet", ...]
        }
      }
    }
    """

    def __init__(self, path: Path = REGISTRY_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"datasets": {}})

    def _read(self) -> Dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: Dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, sort_keys=True, indent=2), encoding="utf-8")

    def register_partition(self, dataset_name: str, partition_relative_path: str) -> None:
        data = self._read()
        datasets = data.setdefault("datasets", {})
        ds = datasets.setdefault(dataset_name, {})
        parts = ds.setdefault("partitions", [])
        if partition_relative_path not in parts:
            parts.append(partition_relative_path)
            logger.info({"event": "register_partition", "dataset": dataset_name, "partition": partition_relative_path})
            self._write(data)

    def list_datasets(self) -> Dict[str, Any]:
        return self._read().get("datasets", {})


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def write_parquet(records: Iterable[Dict[str, Any]], output_path: Path) -> None:
    """Write records to a Parquet file using pyarrow if available.

    If pyarrow is not installed, write NDJSON fallback with .ndjson suffix.
    """
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except Exception as e:
        # Fallback: write NDJSON
        out_ndjson = output_path.with_suffix(output_path.suffix + ".ndjson")
        with out_ndjson.open("w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        logger.warning({"event": "pyarrow_missing", "msg": str(e), "wrote": str(out_ndjson)})
        return

    tbl = pa.Table.from_pylist(list(records))
    _ensure_dir(output_path.parent)
    pq.write_table(tbl, str(output_path))
    logger.info({"event": "parquet_written", "path": str(output_path), "rows": tbl.num_rows})


def partition_and_write(dataset: str, timeframe: str, window_start_ts: int, records: Iterable[Dict[str, Any]], registry: DatasetRegistry) -> Path:
    """Write records into partitioned path and register it.

    Partition layout: data/parquet/feed={dataset}/timeframe={timeframe}/date=YYYY-MM-DD/part-<ts>.parquet
    """
    ts_dt = datetime.utcfromtimestamp(window_start_ts / 1000)
    date_str = ts_dt.strftime("%Y-%m-%d")
    base = BASE_PARQUET_ROOT / f"feed={dataset}" / f"timeframe={timeframe}" / f"date={date_str}"
    out_fn = f"part-{window_start_ts}.parquet"
    out_path = base / out_fn
    write_parquet(records, out_path)
    # register relative path from data/parquet root
    rel = str(out_path.relative_to(BASE_PARQUET_ROOT))
    registry.register_partition(f"feed={dataset}", rel)
    return out_path
