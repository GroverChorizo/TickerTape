"""Strategy loader that runs user code in a subprocess."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import shutil
import uuid
from pathlib import Path
from typing import List, Optional, Sequence


def run_strategy_file(
    strategy_path: str,
    prices: Sequence[float],
    *,
    seed: Optional[int] = None,
    confirm_exec: bool = False,
    timeout_s: int = 30,
) -> List[float]:
    if not confirm_exec:
        raise PermissionError("Strategy execution requires explicit confirmation")
    path = Path(strategy_path)
    if not path.exists():
        raise FileNotFoundError(f"Strategy not found: {strategy_path}")
    if path.suffix.lower() != ".py":
        raise ValueError("Strategy must be a .py file")

    tmp_root = Path(__file__).resolve().parents[1] / "_pytest_local_tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)
    run_dir = tmp_root / f"strategy_{uuid.uuid4().hex[:10]}"
    run_dir.mkdir(parents=True, exist_ok=True)
    try:
        in_path = run_dir / "input.json"
        out_path = run_dir / "output.json"
        in_path.write_text(
            json.dumps({"prices": list(prices), "seed": seed}), encoding="utf-8"
        )

        cmd = [
            sys.executable,
            "-m",
            "backtesting.strategy_runner",
            "--strategy",
            str(path),
            "--input",
            str(in_path),
            "--output",
            str(out_path),
        ]
        env = os.environ.copy()
        env["TICKERTAPE_STRATEGY_EXEC"] = "1"
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"Strategy run failed: {stderr}")
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        curve = payload.get("equity_curve") or []
        return [float(v) for v in curve]
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


__all__ = ["run_strategy_file"]
