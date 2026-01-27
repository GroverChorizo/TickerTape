import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)
from pathlib import Path
from backend.storage import DatasetRegistry
from backend.liquidations_feed import LiquidationsFeed
from backend.snapshotter import run_once


def test_run_once_writes_partition(tmp_path, monkeypatch):
    # Use a temp data/parquet root
    base = tmp_path / "data" / "parquet"
    monkeypatch.setenv("PYTHONPATH", "")
    # Monkeypatch module constant
    from src.backend import storage

    storage.BASE_PARQUET_ROOT = base

    registry = DatasetRegistry(path=base / "_registry.json")
    feed = LiquidationsFeed()

    path_str = run_once(feed, registry, "1h")
    path = Path(path_str)

    assert path.exists() or path.with_suffix(path.suffix + ".ndjson").exists()
    # Registry should have an entry
    datasets = registry.list_datasets()
    assert "feed=liquidations_snapshots" in datasets
    parts = datasets["feed=liquidations_snapshots"].get("partitions", [])
    assert any("timeframe=1h" in p for p in parts)


def test_tools_run_ingestion_cli(tmp_path, monkeypatch):
    # Ensure the tools helper writes partitions
    base = tmp_path / "data" / "parquet"
    from tools.run_ingestion_impl import run_ingestion_impl
    from src.backend import storage

    storage.BASE_PARQUET_ROOT = base
    run_ingestion_impl("liquidations_dashboard", once=True)

    registry = storage.DatasetRegistry(path=base / "_registry.json")
    datasets = registry.list_datasets()
    assert "feed=liquidations_snapshots" in datasets
    # ensure at least one timeframe partition exists
    parts = datasets["feed=liquidations_snapshots"].get("partitions", [])
    assert any("timeframe=1h" in p for p in parts)
