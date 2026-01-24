from pathlib import Path
import subprocess
import sys

from pathlib import Path
import subprocess
import sys

def find_repo_root(start: Path) -> Path:
    p = start.resolve()
    for candidate in [p] + list(p.parents):
        if (candidate / ".git").exists():
            return candidate
        if (candidate / "requirements.txt").exists() or (candidate / "pyproject.toml").exists() or (candidate / ".data_integrity_gate.json").exists():
            return candidate
    raise RuntimeError(f"Could not find repo root from {start}")

def test_data_integrity_gate_scoped_to_tickertape() -> None:
    root = find_repo_root(Path(__file__))
    gate_path = root / "tools" / "data_integrity_gate.py"
    assert gate_path.exists(), f"Gate not found at {gate_path}"
    cmd = [sys.executable, str(gate_path), "--ci", "--root", str(root)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssertionError(
            "Data Integrity Gate failed.\n\nSTDOUT:\n"
            + proc.stdout
            + "\nSTDERR:\n"
            + proc.stderr
        )
