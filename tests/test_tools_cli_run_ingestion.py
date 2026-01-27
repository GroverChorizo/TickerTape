import subprocess
import sys
from pathlib import Path


def test_tools_run_ingestion_cli_executes(tmp_path, monkeypatch):
    # Run the CLI script to ensure it executes without error
    # Use tmp_path as working dir to avoid writing to repo
    script = Path(__file__).resolve().parents[1] / "tools" / "run_ingestion.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--profile", "liquidations_dashboard", "--once"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
