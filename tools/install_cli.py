"""Install the TickerTape CLI entry points into the active environment."""

from __future__ import annotations

import subprocess
import sys


def main() -> int:
    return subprocess.call([sys.executable, "-m", "pip", "install", "-e", "."])


if __name__ == "__main__":
    raise SystemExit(main())
