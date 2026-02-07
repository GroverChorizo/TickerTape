"""
Secrets loader for TickerTape.

Goal: make secrets handling predictable, local-first, and user-friendly.

This module loads secrets from a single secrets file located OUTSIDE the repository.

Key behaviors:
- The app uses an external "Secrets Home" directory by default (canonical),
  and will create it if missing.
- Users may override the secrets directory via `TICKERTAPE_SECRETS_DIR`.
- Users may override the secrets file path via any of:
    - HL_DONT_SHARE_PATH
    - HLDONT_SHARE_PATH
    - TICKERTAPE_SECRETS_PATH
- Default secrets file name is: `HLdontShare.env` within Secrets Home.
- The loader returns a dict of key/value pairs parsed from a .env-style file (KEY=VALUE lines).

Security notes:
- This module does NOT mutate global environment variables.
- Callers may choose to apply returned secrets into `os.environ` if desired.
- This module never prints/logs secret values.

UX support:
- Callers can use `resolve_secrets_file_path()` and `secrets_home_dir()` to
  show users where to place secrets when auth fails.

Typical file contents:
    MOONDEV_API_KEY=...
    HYPERLIQUID_API_KEY=...
"""

from __future__ import annotations

from dataclasses import dataclass
import platform
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple
import os
import sys


# Environment variable for secrets directory override
_ENV_DIR_VAR = "TICKERTAPE_SECRETS_DIR"
# Default secrets file name
_DEFAULT_FILENAME = "HLdontShare.env"
# Environment variables for secrets file path override
_ENV_PATH_VARS = ["HL_DONT_SHARE_PATH", "HLDONT_SHARE_PATH", "TICKERTAPE_SECRETS_PATH"]
_DEFAULT_PATH = Path.home() / ".tickertape" / "secrets" / "HLdontShare.env"
_ENV_VARS = ["HL_DONT_SHARE_PATH", "HLDONT_SHARE_PATH", "TICKERTAPE_SECRETS_PATH"]
_MOONDEV_ENV = "MOONDEV_API_KEY"
_CONFIG_ENV = "TICKERTAPE_CONFIG_PATH"


# Represents the location of secrets home and file
@dataclass
class SecretsLocation:
    secrets_home: Path
    secrets_file: Path
    source: str


def _default_config_path() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home()))
        return base / "TickerTape" / "config.env"
    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "TickerTape"
            / "config.env"
        )
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "tickertape" / "config.env"


def _default_config_path() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home()))
        return base / "TickerTape" / "config.env"
    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "TickerTape"
            / "config.env"
        )
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "tickertape" / "config.env"


def _parse_env_file(path: Path) -> Dict[str, str]:
    """Parse KEY=VALUE lines from a .env-style file. Returns empty dict on error."""
    data: Dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return {}

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        # Strip surrounding quotes but preserve inner characters
        val = val.strip().strip('"').strip("'")
        data[key] = val
    return data


def _windows_appdata_dir() -> Path:
    # Prefer Roaming AppData
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata)
    # Fallback
    return Path.home() / "AppData" / "Roaming"


def _default_secrets_home_dir() -> Path:
    """
    Canonical default secrets home directory (all OSes).

    Windows/macOS/Linux: ~/.tickertape/secrets
    """
    return Path.home() / ".tickertape" / "secrets"


def canonical_secrets_file_path() -> Path:
    """Return the canonical secrets file path (no overrides)."""
    return (Path.home() / ".tickertape" / "secrets" / _DEFAULT_FILENAME).resolve()


def legacy_secrets_file_path() -> Optional[Path]:
    """Return legacy AppData secrets path on Windows, if it exists."""
    system = platform.system().lower()
    if "windows" not in system:
        return None
    legacy = _windows_appdata_dir() / "TickerTape" / "secrets" / _DEFAULT_FILENAME
    return legacy.resolve() if legacy.exists() else None


def secrets_home_dir() -> Path:
    """
    Return the resolved secrets directory (may not exist yet).

    Precedence:
    1) TICKERTAPE_SECRETS_DIR
    2) OS default (see _default_secrets_home_dir)
    """
    override = os.environ.get(_ENV_DIR_VAR)
    if override:
        return Path(override).expanduser().resolve()
    return _default_secrets_home_dir().expanduser().resolve()


def ensure_secrets_home_exists() -> Path:
    """
    Ensure Secrets Home exists (create if missing). Never raises for common failures.
    Returns the resolved secrets home path (even if creation fails).
    """
    home = secrets_home_dir()
    try:
        home.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Do not crash the app for permission/FS issues; caller can handle gracefully.
        pass
    return home


def default_secrets_file_path(path: Optional[Path] = None) -> Path:
    """Return the default secrets file path inside Secrets Home.

    Optional path argument is accepted for backward compatibility and tests.
    """
    if path is not None:
        return Path(path).expanduser().resolve()
    home = ensure_secrets_home_exists()
    return (home / _DEFAULT_FILENAME).resolve()


# Backwards-compatible alias for older tests/callers
_DEFAULT_PATH = default_secrets_file_path()


def resolve_secrets_file_path(
    path: Optional[Path] = None,
    env_var_names: Optional[Iterable[str]] = None,
) -> SecretsLocation:
    """
    Resolve which secrets file to use, and where it should live.

    Precedence:
    1) Env var pointing to a secrets FILE (HL_DONT_SHARE_PATH, etc.)
    2) Explicit `path` argument
    3) Default secrets file in Secrets Home (created outside repo)

    Returns:
        SecretsLocation with secrets_home and secrets_file (may not exist).
    """
    ensure_secrets_home_exists()
    envs = tuple(env_var_names) if env_var_names else _ENV_PATH_VARS

    # 1) Env vars for explicit file
    for name in envs:
        p = os.environ.get(name)
        if not p:
            continue
        candidate = Path(p).expanduser().resolve()
        if candidate.exists() and candidate.is_file():
            return SecretsLocation(
                secrets_home=secrets_home_dir(),
                secrets_file=candidate,
                source=f"env_path_var:{name}",
            )

    # 2) Explicit path argument
    if path is not None:
        candidate = Path(path).expanduser().resolve()
        if candidate.exists() and candidate.is_file():
            return SecretsLocation(
                secrets_home=secrets_home_dir(),
                secrets_file=candidate,
                source="explicit_path",
            )
        # If explicit path provided but doesn't exist, still return it as the intended target
        return SecretsLocation(
            secrets_home=secrets_home_dir(),
            secrets_file=candidate,
            source="explicit_path_missing",
        )

    # 3) Default path
    return SecretsLocation(
        secrets_home=secrets_home_dir(),
        secrets_file=Path(_DEFAULT_PATH).expanduser().resolve(),
        source="default",
    )


def load_secrets(
    path: Optional[Path] = None,
    env_var_names: Optional[Iterable[str]] = None,
) -> Dict[str, str]:
    """
    Load secrets from environment path override or a file.

    Note: This function does NOT read individual secret values from env vars (like MOONDEV_API_KEY);
    it reads a secrets FILE path from env vars, then parses that file.
    If you also want direct env var secrets, do that in a higher layer (recommended).

    Args:
        path: Optional explicit Path to a secrets file.
        env_var_names: Optional override list of env var names that contain a secrets file path.

    Returns:
        Dictionary of secret key/value pairs. Empty dict if no secrets found or file unreadable.
    """
    loc = resolve_secrets_file_path(path=path, env_var_names=env_var_names)
    if loc.secrets_file.exists() and loc.secrets_file.is_file():
        return _parse_env_file(loc.secrets_file)
    return {}


def ensure_secrets_file(path: Optional[Path] = None) -> Tuple[Path, bool]:
    """Ensure the canonical secrets file exists; return (path, created)."""
    loc = resolve_secrets_file_path(path=path)
    target = loc.secrets_file
    if target.exists():
        return target, False
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_placeholder_env(), encoding="utf-8")
        return target, True
    except Exception:
        return target, False


def resolve_moondev_api_key(
    *,
    config_path: Optional[Path] = None,
    dotenv_path: Optional[Path] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Resolve MoonDev API key from the canonical secrets file only."""
    _ = config_path
    _ = dotenv_path
    try:
        secrets_loc = resolve_secrets_file_path()
        secrets = load_secrets(path=secrets_loc.secrets_file)
        val = secrets.get(_MOONDEV_ENV) or secrets.get("moondev_api_key")
        if val:
            return val.strip(), f"secrets:{secrets_loc.secrets_file}"
    except Exception:
        return None, None
    return None, None


def moondev_config_help() -> str:
    secrets_path = str(resolve_secrets_file_path().secrets_file)
    return (
        "MoonDev API key missing. Add it to:\n"
        f"- {secrets_path}\n"
        "Format: MOONDEV_API_KEY=your_key"
    )


def _placeholder_env() -> str:
    return (
        "# TickerTape secrets (local-only)\n"
        "# Add your API keys below. Keep this file private.\n"
        "MOONDEV_API_KEY=\n"
        "HYPERLIQUID_API_KEY=\n"
    )


__all__ = [
    "load_secrets",
    "ensure_secrets_file",
    "_DEFAULT_PATH",
    "canonical_secrets_file_path",
    "legacy_secrets_file_path",
    "resolve_moondev_api_key",
    "moondev_config_help",
]
