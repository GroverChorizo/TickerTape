import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tui.config import TuiConfig, config_needs_setup, ensure_data_root, load_config, save_config


def test_config_round_trip(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    data_root = tmp_path / "data" / "parquet"
    config = TuiConfig(
        mode="offline_demo",
        data_root=data_root,
        profile="day_trader",
        secrets_path=None,
        config_path=config_path,
    )
    save_config(config)
    loaded = load_config({"config_path": str(config_path)})
    assert loaded.mode == "offline_demo"
    assert loaded.data_root == data_root


def test_ensure_data_root(tmp_path):
    config = TuiConfig(
        mode="offline_demo",
        data_root=tmp_path / "parquet",
        profile="day_trader",
        secrets_path=None,
        config_path=tmp_path / "config.json",
    )
    ensure_data_root(config)
    assert config.data_root.exists()


def test_config_needs_setup(tmp_path):
    config = TuiConfig(
        mode="offline_demo",
        data_root=tmp_path / "parquet",
        profile="day_trader",
        secrets_path=None,
        config_path=tmp_path / "config.json",
    )
    assert config_needs_setup(config)
