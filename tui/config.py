"""Configuration management for the TUI."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional
import json
import os


DEFAULT_DATA_ROOT = Path("data/parquet")
DEFAULT_PROFILE = "day_trader"


@dataclass
class TuiConfig:
    mode: str
    data_root: Path
    profile: str
    secrets_path: Optional[Path]
    config_path: Path

    def to_dict(self) -> Dict:
        payload = asdict(self)
        payload["data_root"] = str(self.data_root)
        payload["secrets_path"] = str(self.secrets_path) if self.secrets_path else None
        payload["config_path"] = str(self.config_path)
        return payload


def _env_path(name: str) -> Optional[Path]:
    value = os.environ.get(name)
    if value:
        return Path(value)
    return None


def default_config_path() -> Path:
    env_path = _env_path("TICKERTAPE_CONFIG")
    if env_path:
        return env_path
    repo_default = Path(".tickertape") / "config.json"
    if repo_default.exists():
        return repo_default
    return Path.home() / ".tickertape" / "config.json"


def load_config(overrides: Optional[Dict[str, str]] = None) -> TuiConfig:
    overrides = overrides or {}
    path = Path(overrides.get("config_path") or default_config_path())
    payload: Dict[str, str] = {}
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    mode = (
        overrides.get("mode")
        or os.environ.get("TICKERTAPE_MODE")
        or payload.get("mode")
        or "offline_demo"
    )
    data_root = Path(
        overrides.get("data_root")
        or os.environ.get("TICKERTAPE_DATA_ROOT")
        or payload.get("data_root")
        or DEFAULT_DATA_ROOT
    )
    profile = (
        overrides.get("profile")
        or os.environ.get("TICKERTAPE_PROFILE")
        or payload.get("profile")
        or DEFAULT_PROFILE
    )
    secrets_path = (
        overrides.get("secrets_path")
        or os.environ.get("TICKER_TAPE_SECRETS_PATH")
        or os.environ.get("TICKERTAPE_SECRETS_PATH")
        or payload.get("secrets_path")
    )
    return TuiConfig(
        mode=mode,
        data_root=data_root,
        profile=profile,
        secrets_path=Path(secrets_path) if secrets_path else None,
        config_path=path,
    )


def save_config(config: TuiConfig) -> None:
    config.config_path.parent.mkdir(parents=True, exist_ok=True)
    config.config_path.write_text(
        json.dumps(config.to_dict(), indent=2, sort_keys=True), encoding="utf-8"
    )


def ensure_data_root(config: TuiConfig) -> None:
    config.data_root.mkdir(parents=True, exist_ok=True)


def config_needs_setup(config: TuiConfig) -> bool:
    if not config.config_path.exists():
        return True
    if not config.data_root:
        return True
    return False
