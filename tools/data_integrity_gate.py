#!/usr/bin/env python3
"""
Data Integrity Gate — Institutional Guardrail

Enforces (baseline):
- No synthetic/fake/random data generation in production code paths.
- No obvious lookahead bias patterns (e.g., shift(-1)) in strategy/backtest logic.
- No unsafe dynamic execution (eval/exec) or unsafe deserialization (pickle.loads) on untrusted inputs.
- Best-effort detection of possible secret logging.

This script is intentionally conservative: it flags suspicious patterns.
If you need an exception, add it to the allowlist with a justification in the PR.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

DEFAULT_EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache",
    "node_modules", "dist", "build", ".ruff_cache"
}

DEFAULT_INCLUDE_EXTS = {".py", ".md", ".txt", ".yaml", ".yml", ".toml", ".json"}

PATTERNS = {
    "synthetic_or_fake_data": [
        r"\bsynthetic data\b",
        r"\bfake data\b",
        r"\brandom\.uniform\(",
        r"\brandom\.randint\(",
        r"\bnp\.random\.",
        r"\bfaker\b",
        r"\bMock\b",
        r"\bSIMULATE\b",
        r"\bsimulat(e|ed|ion)\b",
    ],
    "lookahead_bias": [
        r"\.shift\(\s*-\s*1\s*\)",
        r"\.shift\(\s*-\s*\d+\s*\)",
        r"\bforward\s*fill\b",
        r"\bffill\(\)",
    ],
    "unsafe_execution": [
        # ...existing content from canonical script...
    ],
}

# ...rest of canonical script from AlgoStuff/tools/data_integrity_gate.py...
