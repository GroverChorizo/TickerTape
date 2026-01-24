#!/usr/bin/env python3
"""Run ingestion pipelines (snapshot emission) for local testing.

Usage:
    python tools/run_ingestion.py --profile liquidations_dashboard --once
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from pathlib import Path
# Ensure repo root is on sys.path when run as a script
_repo_root = Path(__file__).resolve().parents[1]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from tools.run_ingestion_impl import run_ingestion_impl


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True)
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()

    run_ingestion_impl(args.profile, once=args.once)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())