import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.storage import DatasetRegistry
from tui.state.datasets import load_datasets


def test_load_datasets_timeframes(tmp_path):
    registry = DatasetRegistry(path=tmp_path / "_registry.json")
    registry.register_partition("feed=liquidations_snapshots", "timeframe=1h/date=2026-01-01/part-1.parquet")
    registry.register_partition("feed=liquidations_snapshots", "timeframe=4h/date=2026-01-01/part-2.parquet")
    datasets = load_datasets(registry)
    info = datasets["feed=liquidations_snapshots"]
    assert "1h" in info.timeframes
    assert "4h" in info.timeframes
