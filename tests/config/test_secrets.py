from __future__ import annotations

import os
from pathlib import Path

import pytest

from config.secrets import (
    check_permissions,
    ensure_secrets_file,
    load_secrets,
    resolve_secrets_path,
)


def test_resolve_secrets_path_prefers_cli_over_env(tmp_path, monkeypatch):
    env_path = tmp_path / "env.yaml"
    cli_path = tmp_path / "cli.yaml"
    monkeypatch.setenv("TICKER_TAPE_SECRETS_PATH", str(env_path))
    resolved = resolve_secrets_path(cli_path)
    assert resolved == cli_path.resolve()


def test_ensure_secrets_file_creates_placeholders(tmp_path):
    path = tmp_path / "secrets.yaml"
    resolved, created = ensure_secrets_file(path)
    assert created is True
    assert resolved.exists()
    text = resolved.read_text(encoding="utf-8")
    assert "hyperliquid_api_key" in text


def test_load_secrets_reads_yaml(tmp_path):
    path = tmp_path / "secrets.yaml"
    path.write_text(
        "hyperliquid_api_key: abc\nmoondev_api_key: def\n", encoding="utf-8"
    )
    data = load_secrets(path)
    assert data.get("hyperliquid_api_key") == "abc"
    assert data.get("moondev_api_key") == "def"


def test_check_permissions_windows_no_warning(tmp_path):
    path = tmp_path / "secrets.yaml"
    path.write_text("hyperliquid_api_key: abc\n", encoding="utf-8")
    if os.name == "nt":
        assert check_permissions(path) is None
    else:
        warning = check_permissions(path)
        assert warning is None or "permissions" in warning
