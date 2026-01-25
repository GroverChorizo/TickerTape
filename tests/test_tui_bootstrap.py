import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend import storage as storage_module
from backend.storage import DatasetRegistry
from tui.bootstrap import bootstrap_data
from tui.config import TuiConfig, DEFAULT_THEME
from tui.diagnostics import collect_diagnostics


def test_bootstrap_creates_registry(tmp_path, monkeypatch):
    data_root = tmp_path / "data" / "parquet"
    config = TuiConfig(
        mode="offline_demo",
        data_root=data_root,
        profile="day_trader",
        theme=DEFAULT_THEME,
        secrets_path=None,
        config_path=tmp_path / "config.json",
    )
    monkeypatch.setattr(storage_module, "BASE_PARQUET_ROOT", data_root)
    monkeypatch.setattr(storage_module, "REGISTRY_PATH", data_root / "_registry.json")

    bootstrap_data(config)
    assert (data_root / "_registry.json").exists()


def test_diagnostics_redacts_secrets(tmp_path):
    data_root = tmp_path / "data" / "parquet"
    data_root.mkdir(parents=True)
    registry = DatasetRegistry(path=data_root / "_registry.json")
    config = TuiConfig(
        mode="offline_demo",
        data_root=data_root,
        profile="day_trader",
        theme=DEFAULT_THEME,
        secrets_path=Path("/tmp/secret.env"),
        config_path=tmp_path / "config.json",
    )
    diagnostics = collect_diagnostics(config, registry)
    assert diagnostics["secrets_path"] == "/tmp/secret.env"
    assert "API_KEY" not in "\n".join(str(v) for v in diagnostics.values())
