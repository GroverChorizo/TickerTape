"""Commands to list and inspect local backtest jobs."""

from __future__ import annotations

import json
import os
from typing import Optional

from backtesting.job import DEFAULT_ROOT, read_metadata, read_result


def _list_runs(root: str) -> list[str]:
    if not os.path.isdir(root):
        return []
    try:
        entries = sorted([e for e in os.listdir(root) if os.path.isdir(os.path.join(root, e))])
        return entries
    except Exception:
        return []


def jobs_command(cmd: str, args: list[str]) -> Optional[str]:
    """Usage: :jobs list [--root PATH] | :jobs show <run_id> [--root PATH]"""
    if not args:
        return "Usage: :jobs list [--root PATH] | :jobs show <run_id> [--root PATH]"
    sub = args[0]
    root = DEFAULT_ROOT
    if "--root" in args:
        try:
            i = args.index("--root")
            root = args[i + 1]
        except Exception:
            return "Error: invalid --root usage"
    if sub == "list":
        runs = _list_runs(root)
        if not runs:
            return f"No runs found in {root}"
        lines = [f"Runs in {root}:"]
        for r in runs:
            lines.append(f"- {r}")
        return "\n".join(lines)
    if sub == "show":
        if len(args) < 2:
            return "Usage: :jobs show <run_id> [--root PATH]"
        run_id = args[1]
        run_dir = os.path.join(root, run_id)
        if not os.path.isdir(run_dir):
            return f"Run not found: {run_id}"
        try:
            meta = read_metadata(run_dir)
        except Exception as e:
            return f"Error reading metadata: {e}"
        try:
            res = read_result(run_dir)
        except Exception:
            res = None
        out = {
            "metadata": meta,
            "result_summary": {
                "points": len(res.get("equity_curve", [])) if res else None,
                "metrics": res.get("metrics") if res else None,
            },
        }
        return json.dumps(out, indent=2)
    return "Unknown subcommand. Use 'list' or 'show'."