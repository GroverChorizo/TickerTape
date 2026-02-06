"""Minimal local job store for backtests."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Dict, Any

from .models import BacktestJobMetadata, BacktestResult


DEFAULT_ROOT = os.path.expanduser("~/.ticker_tape/jobs")


def _ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def new_run_dir(root: str = DEFAULT_ROOT, run_id: str | None = None) -> str:
    run_id = run_id or uuid.uuid4().hex[:8]
    path = os.path.join(root, run_id)
    _ensure_dir(path)
    return path


def write_metadata(metadata: BacktestJobMetadata, root: str = DEFAULT_ROOT) -> str:
    path = new_run_dir(root, metadata.run_id)
    meta_path = os.path.join(path, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(metadata.to_dict(), fh, indent=2)
    return meta_path


def write_result(result: BacktestResult, root: str = DEFAULT_ROOT) -> str:
    path = new_run_dir(root, result.run_id)
    result_path = os.path.join(path, "result.json")
    with open(result_path, "w", encoding="utf-8") as fh:
        json.dump(result.to_dict(), fh, default=str, indent=2)
    return result_path


def read_metadata(run_dir: str) -> Dict[str, Any]:
    meta_path = os.path.join(run_dir, "metadata.json")
    with open(meta_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def read_result(run_dir: str) -> Dict[str, Any]:
    result_path = os.path.join(run_dir, "result.json")
    with open(result_path, "r", encoding="utf-8") as fh:
        return json.load(fh)
