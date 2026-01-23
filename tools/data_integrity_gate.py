"""TickerTape-local gate wrapper that delegates to repo-level canonical gate.

This script exists so that TickerTape can be checked locally via its usual path
but all logic lives in the canonical tools/data_integrity_gate.py at repo root.
"""
from __future__ import annotations
import runpy
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec

ROOT = Path(__file__).resolve().parents[3]
GATE = ROOT / "tools" / "data_integrity_gate.py"

# Import the canonical gate implementation from the repo-root tools directory
# Load canonical gate module in an isolated namespace and re-export helpers
_module_globals = runpy.run_path(str(GATE))
run_checks = _module_globals.get("run_checks")
main = _module_globals.get("main")

if run_checks is None or main is None:
    raise ImportError("Could not import run_checks/main from canonical data_integrity_gate.py")

if __name__ == "__main__":
    # preserve previous behavior for CLI entry
    runpy.run_path(str(GATE), run_name="__main__")
