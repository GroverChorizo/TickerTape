import os
from pathlib import Path
import pytest

from backend.secrets import load_secrets, _DEFAULT_PATH


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_load_secrets_from_explicit_path(tmp_path):
    p = tmp_path / "HLdontShare.env"
    write_file(p, "API_KEY=abc123\nMOONDEV_API_KEY=moon\n# comment\n")

    data = load_secrets(path=p)
    assert data["API_KEY"] == "abc123"
    assert data["MOONDEV_API_KEY"] == "moon"


def test_load_secrets_from_env_var(monkeypatch, tmp_path):
    p = tmp_path / "HLdontShare.env"
    write_file(p, "X=1\nY=2\n")
    monkeypatch.setenv("HL_DONT_SHARE_PATH", str(p))

    data = load_secrets()
    assert data["X"] == "1"
    assert data["Y"] == "2"


def test_load_secrets_default_fallback(monkeypatch, tmp_path):
    # Monkeypatch the module default path to a temp file
    monkeypatch.setattr("backend.secrets._DEFAULT_PATH", tmp_path / "HLdontShare.env")
    write_file(tmp_path / "HLdontShare.env", "A=alpha\n")

    data = load_secrets()
    assert data.get("A") == "alpha"


def test_load_secrets_no_file_returns_empty(tmp_path):
    data = load_secrets(path=tmp_path / "nonexistent.env")
    assert data == {}
