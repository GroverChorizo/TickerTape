from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_entrypoints_declared_in_setup():
    setup_path = Path(__file__).resolve().parents[1] / "setup.py"
    text = setup_path.read_text(encoding="utf-8")
    assert "TickerTape" in text
    assert "TTape" in text
    assert "tui.app:run" in text


def test_app_help_runs():
    result = subprocess.run(
        [sys.executable, "-m", "tui.app", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
