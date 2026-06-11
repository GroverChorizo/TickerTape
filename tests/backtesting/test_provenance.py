from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from backtesting.job import SCHEMA_NAME, SCHEMA_VERSION, read_metadata, read_result
from backtesting.runner import run_from_file


def _checksum(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def test_runner_outputs_match_golden_checksums(tmp_path):
    fixture = Path(__file__).with_name("fixtures") / "example_strategy.py"
    strategy = tmp_path / "example_strategy.py"
    strategy.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    def fixed_clock() -> int:
        return next(clock_values)

    # Run #1
    clock_values = iter([1_700_000_000_000, 1_700_000_000_250])
    run1_root = str(tmp_path / "jobs_run1")
    run_from_file(
        str(strategy),
        prices=[100.0, 102.5, 101.25, 104.0],
        dataset="fixture://example_prices",
        seed=11,
        run_id="golden-run",
        job_root=run1_root,
        confirm_exec=True,
        time_ms_fn=fixed_clock,
    )
    run1_dir = os.path.join(run1_root, "golden-run")
    meta_1 = read_metadata(run1_dir)
    result_1 = read_result(run1_dir)
    meta_checksum_1 = _checksum(meta_1)
    result_checksum_1 = _checksum(result_1)

    # Run #2: same inputs produce the same artifacts.
    clock_values = iter([1_700_000_000_000, 1_700_000_000_250])
    run2_root = str(tmp_path / "jobs_run2")
    run_from_file(
        str(strategy),
        prices=[100.0, 102.5, 101.25, 104.0],
        dataset="fixture://example_prices",
        seed=11,
        run_id="golden-run",
        job_root=run2_root,
        confirm_exec=True,
        time_ms_fn=fixed_clock,
    )
    run2_dir = os.path.join(run2_root, "golden-run")
    meta_2 = read_metadata(run2_dir)
    result_2 = read_result(run2_dir)

    assert _checksum(meta_2) == meta_checksum_1
    assert _checksum(result_2) == result_checksum_1

    # Golden checksums guard against unnoticed deterministic output drift.
    assert meta_checksum_1 == "8e87d225501ff54d309238c79e0416e4c32f1a9f6080cf727e036f38fc18f663"
    assert result_checksum_1 == "0e3e21c29045d9afd438d4164d5728dbc0224749a3fb799bf3bc587d0b907d69"


def test_read_metadata_migrates_legacy_schema(tmp_path):
    run_dir = tmp_path / "legacy"
    run_dir.mkdir(parents=True, exist_ok=True)
    legacy_payload = {
        "run_id": "legacy01",
        "strategy": "legacy.py",
        "strategy_version": "0.1",
        "dataset": "fixture://legacy",
        "params": {"window": 5},
        "seed": 7,
        "started_at_ms": 10,
        "finished_at_ms": 20,
    }
    (run_dir / "metadata.json").write_text(
        json.dumps(legacy_payload), encoding="utf-8"
    )
    loaded = read_metadata(str(run_dir))
    assert loaded["run_id"] == "legacy01"
    assert loaded["_schema"] == {"name": SCHEMA_NAME, "version": SCHEMA_VERSION}


def test_read_result_rejects_unknown_schema_version(tmp_path):
    run_dir = tmp_path / "future"
    run_dir.mkdir(parents=True, exist_ok=True)
    future_payload = {
        "_schema": {"name": SCHEMA_NAME, "version": "2.0.0"},
        "run_id": "future01",
        "timestamps": [0],
        "equity_curve": [100.0],
        "metrics": {"start": 100.0, "end": 100.0, "return": 0.0},
        "trades": [],
        "signals": [],
    }
    (run_dir / "result.json").write_text(json.dumps(future_payload), encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported provenance schema version '2.0.0'"):
        read_result(str(run_dir))
