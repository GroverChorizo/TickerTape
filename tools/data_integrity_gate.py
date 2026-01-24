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
        r"\beval\(",
        r"\bexec\(",
        r"\bpickle\.loads\(",
        r"\bmarshal\.loads\(",
    ],
    "possible_secret_logging": [
        r"logger\.(debug|info|warning|error)\(.*(api[_-]?key|secret|token|private[_-]?key).*",
        r"print\(.*(api[_-]?key|secret|token|private[_-]?key).*",
    ],
}

@dataclass
class Finding:
    category: str
    file: Path
    line_no: int
    line: str
    pattern: str

def load_config(config_path: Optional[Path]) -> dict:
    if not config_path or not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[gate] Failed to parse config: {config_path} ({e})", file=sys.stderr)
        return {}

def iter_files(root: Path, exclude_dirs: set[str], include_exts: set[str]) -> Iterable[Path]:
    for p in root.rglob("*"):
        if p.is_dir():
            continue
        if p.suffix.lower() not in include_exts:
            continue
        if any(part in exclude_dirs for part in p.parts):
            continue
        yield p

def scan_file(path: Path, compiled: List[Tuple[str, re.Pattern]]) -> List[Finding]:
    findings: List[Finding] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return findings

    for i, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        # Ignore full-line comments in Python files (comment-only lines are not executable code)
        if path.suffix.lower() == ".py" and stripped.startswith("#"):
            continue
        for category, rx in compiled:
            if rx.search(line):
                findings.append(Finding(category, path, i, line.strip(), rx.pattern))
    return findings

def is_allowed(f: Finding, allowlist: list[dict]) -> bool:
    fp = str(f.file).replace("\\", "/")
    for rule in allowlist:
        file_prefix = rule.get("file")
        cat = rule.get("category")
        pat_contains = rule.get("pattern_contains")
        if file_prefix and not fp.startswith(file_prefix):
            continue
        if cat and cat != f.category:
            continue
        if pat_contains and pat_contains not in f.pattern:
            continue
        return True
    return False

def _hygiene_checks(root: Path, cfg: dict) -> Tuple[List[str], List[str], List[str]]:
    """Return missing_gitignore_patterns, missing_required_files, present_forbidden_files"""
    req_patterns = cfg.get("required_gitignore_patterns", [])
    req_files = cfg.get("required_files", [])
    forb_files = cfg.get("forbidden_files", [])

    missing_patterns = []
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        missing_patterns = req_patterns[:]
    else:
        text = gitignore.read_text(encoding="utf-8")
        for p in req_patterns:
            if p not in text:
                missing_patterns.append(p)

    missing_required_files = [f for f in req_files if not (root / f).exists()]
    present_forbidden = [f for f in forb_files if (root / f).exists()]

    return missing_patterns, missing_required_files, present_forbidden


def run_checks(root: Path = Path('.'), config_path: str = '.data_integrity_gate.json', ci: bool = False) -> bool:
    """Run the gate checks programmatically.

    Returns True if checks pass (no integrity or hygiene violations), False otherwise.
    """
    root = Path(root).resolve()

    # Load config file from the provided root ONLY. Do not search parent folders.
    cfg_path = root / config_path
    if not cfg_path.exists():
        raise RuntimeError(f"Data Integrity Gate misconfigured: config not found at {cfg_path}")

    config = load_config(cfg_path)

    exclude_dirs = set(config.get("exclude_dirs", [])) | DEFAULT_EXCLUDE_DIRS
    include_exts = set(ext.lower() for ext in config.get("include_exts", [])) or DEFAULT_INCLUDE_EXTS
    allowlist = config.get("allowlist", [])

    compiled: List[Tuple[str, re.Pattern]] = []
    for category, patterns in PATTERNS.items():
        for p in patterns:
            compiled.append((category, re.compile(p, re.IGNORECASE)))

    findings: List[Finding] = []

    # Enforce 'scan_roots' configuration strictly (relative to provided root). The gate WILL NOT
    # scan outside of the configured repo root. If no valid scan_roots are found, fail hard.
    scan_roots_cfg = config.get("scan_roots")
    if not scan_roots_cfg:
        raise RuntimeError("Data Integrity Gate misconfigured: 'scan_roots' must be set in the gate config")

    files_to_scan: List[Path] = []
    resolved_scan_dirs: List[Path] = []
    for r in scan_roots_cfg:
        candidate = (root / r).resolve()
        if not candidate.exists() or not candidate.is_dir():
            print(f"[gate] Notice: scan_root not found (skipping): {r}")
            continue
        # Ensure candidate is within root (do not traverse outside provided root)
        try:
            if not candidate.is_relative_to(root):
                raise RuntimeError(f"Data Integrity Gate refusal: scan_root '{r}' would traverse outside repo root")
        except AttributeError:
            # Python <3.9 fallback: ensure root is a parent
            if root not in candidate.parents and candidate != root:
                raise RuntimeError(f"Data Integrity Gate refusal: scan_root '{r}' would traverse outside repo root")

        resolved_scan_dirs.append(candidate)
        files_to_scan.extend(list(iter_files(candidate, exclude_dirs, include_exts)))

    if not files_to_scan:
        raise RuntimeError("Data Integrity Gate misconfigured: no valid scan_roots found under the provided root")

    # Treat 'synthetic_or_fake_data' findings in test or docs files as expected and ignore them.
    # This enforces that integrity violations are about production code only (src).
    filtered_findings: List[Finding] = []
    for ff in findings:
        if ff.category == "synthetic_or_fake_data":
            try:
                rel_fp = ff.file.relative_to(root)
                if "tests" in rel_fp.parts or "docs" in rel_fp.parts:
                    continue
            except Exception:
                # If any odd path handling occurs, keep the finding
                pass
        filtered_findings.append(ff)

    findings = [f for f in filtered_findings if not is_allowed(f, allowlist)]

    for f in files_to_scan:
        findings.extend(scan_file(f, compiled))

    findings = [f for f in findings if not is_allowed(f, allowlist)]

    # Hygiene checks: evaluate hygiene at the configured repo root (never at scan subdirs).
    missing_patterns, missing_required, present_forbidden = _hygiene_checks(root, config)

    ok = True

    if missing_patterns or missing_required or present_forbidden:
        ok = False
        print("[hygiene] FAIL: repository hygiene issues found:\n")
        if missing_patterns:
            print("[hygiene] Missing .gitignore patterns:")
            for p in set(missing_patterns):
                print(f"  - {p}")
        if missing_required:
            print("[hygiene] Missing required files:")
            for p in set(missing_required):
                print(f"  - {p}")
        if present_forbidden:
            print("[hygiene] Forbidden files present:")
            for p in set(present_forbidden):
                print(f"  - {p}")
        print()

    if not findings and ok:
        print("[gate] PASS: no integrity or hygiene violations found.")
        return True

    if findings:
        print("[integrity] FAIL: integrity violations found:\n")
        for f in findings[:500]:
            rel = f.file.relative_to(root)
            print(f"- {f.category}: {rel}:{f.line_no}  pattern=/{f.pattern}/")
            print(f"  {f.line}\n")
        if len(findings) > 500:
            print(f"[integrity] ... plus {len(findings) - 500} more findings (truncated).")

    if ci:
        return False

    print("\n[gate] If a finding is intentional (e.g., tests), add an allowlist rule in .data_integrity_gate.json with a reason.")
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="Repo root to scan (default: .)")
    ap.add_argument("--config", default=".data_integrity_gate.json", help="Optional JSON config path")
    ap.add_argument("--ci", action="store_true", help="CI mode (non-interactive)")
    args = ap.parse_args()

    ok = run_checks(root=Path(args.root), config_path=args.config, ci=args.ci)
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())