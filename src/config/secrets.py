"""Secrets file handling for TickerTape (YAML)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple
import os
import stat
import subprocess
import sys

try:
    import yaml
except Exception:  # pragma: no cover - fallback when PyYAML is unavailable
    yaml = None


ENV_PATH_VARS = ("TICKER_TAPE_SECRETS_PATH", "TICKERTAPE_SECRETS_PATH")
DEFAULT_SECRETS_PATH = Path.home() / ".ticker_tape" / "secrets.yaml"


def resolve_secrets_path(
    cli_path: Optional[Path] = None, env: Optional[Mapping[str, str]] = None
) -> Path:
    """Resolve secrets path: CLI arg > env var > default."""
    if cli_path:
        return Path(cli_path).expanduser().resolve()
    env = env or os.environ
    for key in ENV_PATH_VARS:
        value = env.get(key)
        if value:
            return Path(value).expanduser().resolve()
    return DEFAULT_SECRETS_PATH.expanduser().resolve()


def ensure_secrets_file(path: Path) -> Tuple[Path, bool]:
    """Ensure secrets file exists; return (path, created)."""
    path = Path(path).expanduser().resolve()
    force_create = os.environ.get("TICKERTAPE_FORCE_SECRETS_CREATE") == "1"
    if path.exists() and not force_create:
        _ensure_permissions(path)
        return path, False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_placeholder_yaml(), encoding="utf-8")
    _ensure_permissions(path)
    return path, True


def load_secrets(path: Path) -> Dict[str, Any]:
    """Load secrets from YAML file; returns empty dict if missing or invalid."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except Exception:
        return {}
    try:
        if yaml is None:
            payload = _parse_simple_yaml(text)
        else:
            payload = yaml.safe_load(text) or {}
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def check_permissions(path: Path) -> Optional[str]:
    """Return warning string if permissions are insecure (POSIX), else None."""
    if os.name == "nt":
        return None
    try:
        mode = path.stat().st_mode
    except Exception:
        return "unable to read permissions"
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        return "permissions are too open; recommend chmod 600"
    return None


def open_in_editor(path: Path) -> bool:
    """Open the secrets file in the user's default editor."""
    path = Path(path).expanduser().resolve()
    editor = os.environ.get("EDITOR")
    try:
        if editor:
            subprocess.Popen([editor, str(path)])
            return True
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
            return True
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
            return True
        subprocess.Popen(["xdg-open", str(path)])
        return True
    except Exception:
        return False


def _ensure_permissions(path: Path) -> None:
    if os.name == "nt":
        return
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


def _placeholder_yaml() -> str:
    return (
        "# TickerTape secrets (local-only)\n"
        "# Add your API keys below. Keep this file private.\n"
        'hyperliquid_api_key: ""\n'
        'exchange_api_secret: ""\n'
    )


def _parse_simple_yaml(text: str) -> Dict[str, Any]:
    """Minimal YAML parser for key: value pairs (fallback when PyYAML is missing)."""
    payload: Dict[str, Any] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if not key:
            continue
        value = value.strip().strip('"').strip("'")
        payload[key] = value
    return payload
