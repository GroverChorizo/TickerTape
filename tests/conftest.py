import sys
from pathlib import Path

# Ensure tests import from local src directory and repo tools
ROOT = Path(__file__).resolve().parents[1]
SRC = str(ROOT / "src")
ROOT_STR = str(ROOT)
# Insert root first so packages in repo (e.g., tools) can be imported during tests
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)
if SRC not in sys.path:
    sys.path.insert(0, SRC)
