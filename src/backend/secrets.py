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
from typing import Dict, Iterable, Optional, Tuple
import os
import sys

_DEFAULT_PATH = Path.home() / ".tickertape" / "secrets" / "HLdontShare.env"
_ENV_VARS = ["HL_DONT_SHARE_PATH", "HLDONT_SHARE_PATH", "TICKERTAPE_SECRETS_PATH"]
_MOONDEV_ENV = "MOONDEV_API_KEY"
_CONFIG_ENV = "TICKERTAPE_CONFIG_PATH"


def _default_config_path() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home()))
        return base / "TickerTape" / "config.env"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "TickerTape" / "config.env"
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "tickertape" / "config.env"


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


def resolve_moondev_api_key(
    *,
    config_path: Optional[Path] = None,
    dotenv_path: Optional[Path] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Resolve MoonDev API key from env, config, or .env files.

    Precedence:
    1) Environment variable MOONDEV_API_KEY
    2) Config file (override via TICKERTAPE_CONFIG_PATH)
    3) Optional .env in the current working directory
    """
    env_val = os.environ.get(_MOONDEV_ENV)
    if env_val:
        return env_val.strip(), f"env:{_MOONDEV_ENV}"

    config_candidate = config_path
    if config_candidate is None:
        override = os.environ.get(_CONFIG_ENV)
        if override:
            config_candidate = Path(override).expanduser()
        else:
            config_candidate = _default_config_path()
    if config_candidate and config_candidate.exists() and config_candidate.is_file():
        data = _parse_env_file(config_candidate)
        val = data.get(_MOONDEV_ENV)
        if val:
            return val.strip(), f"config:{config_candidate}"

    env_candidate = dotenv_path or Path.cwd() / ".env"
    if env_candidate.exists() and env_candidate.is_file():
        data = _parse_env_file(env_candidate)
        val = data.get(_MOONDEV_ENV)
        if val:
            return val.strip(), f"dotenv:{env_candidate}"

    return None, None


def moondev_config_help() -> str:
    config_path = os.environ.get(_CONFIG_ENV) or str(_default_config_path())
    return (
        "MoonDev API key missing. Set MOONDEV_API_KEY or place it in:\n"
        f"- {config_path}\n"
        "Format: MOONDEV_API_KEY=your_key\n"
        "You can also use a local .env for dev (gitignored)."
    )


__all__ = ["load_secrets", "_DEFAULT_PATH", "resolve_moondev_api_key", "moondev_config_help"]
