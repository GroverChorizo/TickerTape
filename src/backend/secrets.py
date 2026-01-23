"""Secrets loader for TickerTape

Loads secrets from environment variables or from a secrets file that lives
outside the repository by default (user home under `.tickertape/secrets/`).

Behavior:
- If environment variable `HL_DONT_SHARE_PATH` or `TICKERTAPE_SECRETS_PATH` is set
  and points to a readable file, that file is used.
- Otherwise, a default file is used: `~/.tickertape/secrets/HLdontShare.env`.
- The loader returns a dict of key/value pairs parsed from the file (KEY=VALUE lines).

Notes: This module does NOT mutate global environment variables; callers can choose
to apply the returned secrets into `os.environ` if they wish.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional
import os

_DEFAULT_PATH = Path.home() / ".tickertape" / "secrets" / "HLdontShare.env"
_ENV_VARS = ["HL_DONT_SHARE_PATH", "HLDONT_SHARE_PATH", "TICKERTAPE_SECRETS_PATH"]


def _parse_env_file(path: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            data[key] = val
    except Exception:
        # On any read/parse error, return empty dict - caller may handle missing secrets
        return {}
    return data


def load_secrets(path: Optional[Path] = None, env_var_names: Optional[Iterable[str]] = None) -> Dict[str, str]:
    """Load secrets from environment or a file.

    Args:
        path: Optional explicit Path to a secrets file. If provided and exists, it will be used.
        env_var_names: Optional override list of environment variable names to consult for a path.

    Returns:
        Dictionary of secret key/value pairs. Empty dict if no secrets found.
    """
    envs = list(env_var_names) if env_var_names else _ENV_VARS

    # 1) Check env vars for an explicit path
    for name in envs:
        p = os.environ.get(name)
        if not p:
            continue
        candidate = Path(p).expanduser().resolve()
        if candidate.exists() and candidate.is_file():
            return _parse_env_file(candidate)

    # 2) If explicit path argument provided, use it
    if path is not None:
        candidate = Path(path).expanduser().resolve()
        if candidate.exists() and candidate.is_file():
            return _parse_env_file(candidate)

    # 3) Fallback to default external path outside the repo
    if _DEFAULT_PATH.exists() and _DEFAULT_PATH.is_file():
        return _parse_env_file(_DEFAULT_PATH)

    return {}


__all__ = ["load_secrets", "_DEFAULT_PATH"]
