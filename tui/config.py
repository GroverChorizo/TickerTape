"""Configuration management for the TUI."""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Optional
import json
import os
import sys

from pathlib import Path as _Path

_SRC = _Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from tickertape.core.paths import resolve_config_path as _resolve_config_path
from tickertape.core.paths import resolve_secrets_path as _resolve_secrets_path


DEFAULT_DATA_ROOT = Path("data/parquet")
DEFAULT_PROFILE = "day_trader"
DEFAULT_FUNDING_EXCHANGES = ["hyperliquid", "binance"]


@dataclass
class TuiConfig:
    mode: str
    data_root: Path
    profile: str
    config_path: Path
    secrets_path: Optional[Path]
    alerts: Dict[str, bool] = field(default_factory=dict)
    panel_overrides: Dict[str, list[str]] = field(default_factory=dict)
    funding_exchanges: List[str] = field(
        default_factory=lambda: list(DEFAULT_FUNDING_EXCHANGES)
    )
    # Optional base URL for the opt-in MoonDev Data console (external data
    # layer). None → the DataLayerClient default. Never the primary feed.
    datalayer_base_url: Optional[str] = None

    def to_dict(self) -> Dict:
        payload = asdict(self)
        payload["data_root"] = str(self.data_root)
        payload["secrets_path"] = str(self.secrets_path) if self.secrets_path else None
        payload["config_path"] = str(self.config_path)
        return payload


def default_config_path() -> Path:
    return _resolve_config_path()


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
    secrets_override = (
        overrides.get("secrets_path")
        or os.environ.get("TICKER_TAPE_SECRETS_PATH")
        or os.environ.get("TICKERTAPE_SECRETS_PATH")
        or payload.get("secrets_path")
    )
    secrets_path = _resolve_secrets_path(secrets_override) if secrets_override else None
    datalayer_base_url = (
        overrides.get("datalayer_base_url")
        or os.environ.get("TICKERTAPE_DATALAYER_BASE_URL")
        or payload.get("datalayer_base_url")
        or None
    )
    alerts = payload.get("alerts") or {}
    panel_overrides = payload.get("panel_overrides") or {}
    funding_exchanges = payload.get("funding_exchanges") or DEFAULT_FUNDING_EXCHANGES
    if not isinstance(alerts, dict):
        alerts = {}
    if not isinstance(panel_overrides, dict):
        panel_overrides = {}
    if not isinstance(funding_exchanges, list):
        funding_exchanges = list(DEFAULT_FUNDING_EXCHANGES)
    return TuiConfig(
        mode=mode,
        data_root=data_root,
        profile=profile,
        secrets_path=Path(secrets_path) if secrets_path else None,
        alerts={str(k): bool(v) for k, v in alerts.items()},
        panel_overrides={
            str(k): [str(x) for x in v]
            for k, v in panel_overrides.items()
            if isinstance(v, list)
        },
        funding_exchanges=[str(x) for x in funding_exchanges],
        datalayer_base_url=str(datalayer_base_url) if datalayer_base_url else None,
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


def update_funding_exchanges(
    current: List[str], action: str, exchange: str
) -> tuple[List[str], str]:
    normalized = []
    for value in current:
        name = str(value).strip().lower()
        if name and name not in normalized:
            normalized.append(name)
    target = str(exchange).strip().lower()
    if not target:
        return normalized, "Exchange name required."
    if action == "add":
        if target in normalized:
            return normalized, f"{target} already enabled."
        return [*normalized, target], f"Added {target}."
    if action == "remove":
        if target not in normalized:
            return normalized, f"{target} not in list."
        return [x for x in normalized if x != target], f"Removed {target}."
    return normalized, "Usage: exchange add|remove <name> or exchange list"
