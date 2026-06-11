"""Contract, validation, and disk IO. The rules live here so every writer
and the loader enforce the exact same law.

Contract (see Quant Brain → Data Pipeline Spec):
  columns ts,open,high,low,close,volume · ts = bar OPEN, epoch ms, UTC,
  strictly increasing, no duplicates, closed bars only. Gaps are REPORTED,
  never filled. Funding files: ts,rate,interval_hours (raw rate as published).
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .config import data_dir

CONTRACT_COLS = ["ts", "open", "high", "low", "close", "volume"]
FUNDING_COLS = ["ts", "rate", "interval_hours"]

TIMEFRAME_MS: dict[str, int] = {
    "1m": 60_000, "5m": 300_000, "15m": 900_000,
    "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000,
}

# Anything below this is a seconds-unit timestamp wearing an ms costume.
MIN_MS_EPOCH = 1_000_000_000_000  # 2001-09-09 in ms


class DataContractError(Exception):
    """Raised when a file/frame violates the contract. Fail loudly, never patch."""


def now_ms() -> int:
    return int(time.time() * 1000)


def iso(ts_ms: int | float) -> str:
    return pd.Timestamp(int(ts_ms), unit="ms", tz="UTC").strftime("%Y-%m-%dT%H:%M%Z").replace("UTC", "Z")


# ── Paths ─────────────────────────────────────────────────────────────────
def csv_path(symbol: str, timeframe: str, venue_tag: str | None = None) -> Path:
    name = f"{symbol}.{venue_tag}-{timeframe}.csv" if venue_tag else f"{symbol}-{timeframe}.csv"
    return data_dir() / name


def funding_path(symbol: str, venue: str) -> Path:
    return data_dir() / f"{symbol}.{venue}-funding.csv"


def meta_path(path: Path) -> Path:
    return path.with_name(path.stem + ".meta.json")


# ── Validation ────────────────────────────────────────────────────────────
@dataclass
class ValidationReport:
    path: str
    timeframe: str
    source: str = ""
    rows: int = 0
    ts_min: int | None = None
    ts_max: int | None = None
    n_dupes: int = 0
    gaps: list[tuple[int, int, int]] = field(default_factory=list)  # (first_missing, last_missing, n_bars)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def preflight(self) -> str:
        rng = f"{iso(self.ts_min)} → {iso(self.ts_max)} (UTC)" if self.rows else "—"
        lines = [
            "DATA PREFLIGHT",
            f"  file:        {Path(self.path).name}",
            f"  rows:        {self.rows:,}",
            f"  range:       {rng}",
            f"  gaps > 1bar: {len(self.gaps)}",
            f"  dupe ts:     {self.n_dupes}",
            f"  source:      {self.source or 'unknown'}",
        ]
        for g0, g1, n in self.gaps[:10]:
            lines.append(f"    gap: {iso(g0)} … {iso(g1)}  ({n} bars missing)")
        if len(self.gaps) > 10:
            lines.append(f"    … and {len(self.gaps) - 10} more gaps")
        for e in self.errors:
            lines.append(f"  ERROR: {e}")
        return "\n".join(lines)


def validate(df: pd.DataFrame, timeframe: str, path: str = "<memory>",
             source: str = "") -> ValidationReport:
    """Validate an OHLCV frame against the contract. Never mutates input."""
    rep = ValidationReport(path=str(path), timeframe=timeframe, source=source)

    if timeframe not in TIMEFRAME_MS:
        rep.errors.append(f"unknown timeframe '{timeframe}'")
        return rep
    tf = TIMEFRAME_MS[timeframe]

    missing = [c for c in CONTRACT_COLS if c not in df.columns]
    if missing:
        rep.errors.append(f"missing columns: {missing}")
        return rep
    if len(df) == 0:
        rep.errors.append("no rows")
        return rep

    sub = df[CONTRACT_COLS]
    if sub.isna().any().any():
        bad = int(sub.isna().any(axis=1).sum())
        rep.errors.append(f"{bad} rows contain NaN in contract columns")

    ts = pd.to_numeric(sub["ts"], errors="coerce")
    if ts.isna().any():
        rep.errors.append("non-numeric timestamps present")
        return rep
    ts = ts.astype("int64")

    rep.rows = int(len(sub))
    rep.ts_min, rep.ts_max = int(ts.min()), int(ts.max())

    if rep.ts_min < MIN_MS_EPOCH:
        rep.errors.append(
            f"timestamps are not epoch-milliseconds (min={rep.ts_min}; seconds-unit data?)")
        return rep
    if rep.ts_max > now_ms() + tf:
        rep.errors.append(f"future timestamp {iso(rep.ts_max)} — clock or unit error")

    rep.n_dupes = int(ts.duplicated().sum())
    if rep.n_dupes:
        rep.errors.append(f"{rep.n_dupes} duplicate timestamps")

    s = ts.sort_values()
    sv = s.to_numpy()
    if len(sv) > 1:
        dd = np.diff(sv)
        off_grid = int(((dd % tf) != 0).sum())
        if off_grid:
            rep.errors.append(
                f"{off_grid} intervals off the {timeframe} grid (mixed timeframes or corrupt rows)")
        # gaps: spacing of k*tf with k>1 → k-1 missing bars (REPORTED, never an error)
        for i in np.where(dd > tf)[0]:
            n_missing = int(dd[i] // tf - 1)
            if (dd[i] % tf) == 0 and n_missing > 0:
                rep.gaps.append((int(sv[i] + tf), int(sv[i + 1] - tf), n_missing))

    o, h, lo, c, v = (sub[k].astype(float) for k in ("open", "high", "low", "close", "volume"))
    bad_ohlc = int(((lo > o) | (lo > c) | (lo > h) | (h < o) | (h < c)).sum())
    if bad_ohlc:
        rep.errors.append(f"{bad_ohlc} rows violate low ≤ open,close ≤ high")
    neg_v = int((v < 0).sum())
    if neg_v:
        rep.errors.append(f"{neg_v} rows with negative volume")

    return rep


# ── IO ────────────────────────────────────────────────────────────────────
def read_csv(path: Path) -> pd.DataFrame:
    """Raw read with enforced dtypes. Returns empty contract frame if absent."""
    if not Path(path).exists():
        return pd.DataFrame(columns=CONTRACT_COLS)
    df = pd.read_csv(path)
    if "ts" in df.columns:
        df["ts"] = pd.to_numeric(df["ts"], errors="coerce").astype("Int64").astype("int64")
    return df


def merge_frames(existing: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    """Append-only semantics: union on ts, newest write wins, sorted, deduped."""
    if existing is None or len(existing) == 0:
        merged = new.copy()
    else:
        merged = pd.concat([existing[CONTRACT_COLS], new[CONTRACT_COLS]], ignore_index=True)
    merged = (merged.sort_values("ts")
                    .drop_duplicates(subset="ts", keep="last")
                    .reset_index(drop=True))
    return merged


def write_atomic(df: pd.DataFrame, path: Path, meta: dict | None = None) -> None:
    """tmp-file + os.replace so a crash can never leave a half-written CSV."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.stem + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", newline="") as f:
            df.to_csv(f, index=False)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    if meta is not None:
        m = dict(meta)
        m.update({
            "rows": int(len(df)),
            "ts_min": int(df["ts"].min()) if len(df) and "ts" in df else None,
            "ts_max": int(df["ts"].max()) if len(df) and "ts" in df else None,
            "updated_at_utc": iso(now_ms()),
        })
        meta_path(path).write_text(json.dumps(m, indent=2))


def read_meta(path: Path) -> dict:
    mp = meta_path(Path(path))
    if mp.exists():
        try:
            return json.loads(mp.read_text())
        except json.JSONDecodeError:
            return {}
    return {}
