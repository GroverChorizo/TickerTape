import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from backend.query_helpers import load_latest_snapshot, list_datasets
from backend.storage import DatasetRegistry
from backend import storage


def test_load_latest_snapshot_cli(tmp_path, monkeypatch):
    base = tmp_path / "data" / "parquet"
    storage.BASE_PARQUET_ROOT = base
    registry = DatasetRegistry(path=base / "_registry.json")
    # simulate registry entry
    registry.register_partition("feed=liquidations_snapshots", "timeframe=1h/date=2026-01-01/part-123.parquet")
    # write a ndjson fallback file
    p = base / "feed=liquidations_snapshots" / "timeframe=1h" / "date=2026-01-01" / "part-123.parquet.ndjson"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('{"timeframe":"1h","window_start_ts_ms":123000,"count":0}\n')

    snap = load_latest_snapshot(registry, "feed=liquidations_snapshots", "1h")
    assert snap is not None
    assert snap["timeframe"] == "1h"
    datasets = list_datasets(registry)
    assert "feed=liquidations_snapshots" in datasets
