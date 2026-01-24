from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def test_data_integrity_gate_scoped_to_tickertape() -> None:
    """
    Ensure the integrity gate only scans inside the TickerTape repo root,
    even if this repo is nested inside a larger directory (AlgoStuff).
    """
    tickertape_root = Path(__file__).resolve().parents[1]  # .../TickerTape
    gate_path = tickertape_root / "tools" / "data_integrity_gate.py"

    # If your gate is at repo root instead, change this to tickertape_root / "data_integrity_gate.py"
    assert gate_path.exists(), f"Gate not found at {gate_path}"

    cmd = [sys.executable, str(gate_path), "--ci", "--root", str(tickertape_root)]
    proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.returncode != 0:
        raise AssertionError(
            "Data Integrity Gate failed.\n\nSTDOUT:\n"
            + proc.stdout
            + "\nSTDERR:\n"
            + proc.stderr
        )
