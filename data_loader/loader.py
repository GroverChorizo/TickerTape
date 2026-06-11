"""data_loader.loader — THE ONLY DOOR to market data.

Every consumer (backtest engine, strategies, TickerTape panels, future
executor) reads CSVs through `load()` / `load_funding()`. Nothing else may
call pd.read_csv on price files. This chokepoint is what enforces the
real-data-only constitution and prints the preflight every analysis must show.

Hard behaviors:
  * Contract violations RAISE (DataContractError) — never silently repaired.
  * Gaps are reported in the preflight and left as gaps — never forward-filled.
  * Returns tz-aware UTC DatetimeIndex frames, floats for prices/volume.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# package-or-script import shim (works from repo root either way)
try:
    from datadogs.common import (CONTRACT_COLS, FUNDING_COLS, DataContractError,
                                 csv_path, funding_path, read_csv, read_meta, validate)
except ImportError as e:  # pragma: no cover
    raise ImportError("run from the repo root so the 'datadogs' package is importable") from e

__all__ = ["load", "load_funding", "DataContractError"]


def _to_ms(t) -> int | None:
    if t is None:
        return None
    return int(pd.Timestamp(t, tz="UTC").value // 1_000_000) if not isinstance(t, (int, float)) \
        else int(t)


def load(symbol: str, timeframe: str, start=None, end=None,
         venue_tag: str | None = None, path: str | Path | None = None,
         quiet: bool = False) -> pd.DataFrame:
    """Load one market's bars. Validates, prints preflight, fails loudly.

    start/end: ISO strings, datetimes, or epoch-ms ints (inclusive start,
    exclusive end). venue_tag reads SYMBOL.VENUE-TF.csv research files.
    """
    p = Path(path) if path else csv_path(symbol.upper(), timeframe, venue_tag)
    if not p.exists():
        raise FileNotFoundError(
            f"{p} not found. Fetch real data first: "
            f"python -m datadogs fetch {symbol.upper()} {timeframe}"
            + (f" --venue {venue_tag} --tag-venue" if venue_tag else "")
            + "  — never substitute synthetic data.")

    raw = read_csv(p)
    src = read_meta(p).get("source", "")
    rep = validate(raw, timeframe, path=str(p), source=src)
    if not quiet:
        print(rep.preflight(), file=sys.stderr)
    if not rep.ok:
        raise DataContractError(
            f"{p.name} violates the data contract — fix the file/pipeline, "
            f"do not patch around it:\n{rep.preflight()}")

    df = raw[CONTRACT_COLS].sort_values("ts").reset_index(drop=True)
    s, e = _to_ms(start), _to_ms(end)
    if s is not None:
        df = df[df["ts"] >= s]
    if e is not None:
        df = df[df["ts"] < e]

    idx = pd.to_datetime(df["ts"], unit="ms", utc=True)
    out = df.drop(columns=["ts"]).set_index(idx)
    out.index.name = "time"
    out.attrs.update({"symbol": symbol.upper(), "timeframe": timeframe,
                      "source": src, "path": str(p)})
    return out


def load_funding(symbol: str, venue: str = "hyperliquid", start=None, end=None,
                 quiet: bool = False) -> pd.DataFrame:
    """Load raw funding history (rate as published + interval_hours).
    Annualized column added for convenience; raw column remains canonical."""
    p = funding_path(symbol.upper(), venue)
    if not p.exists():
        raise FileNotFoundError(
            f"{p} not found. Fetch it: python -m datadogs funding {symbol.upper()} --venue {venue}")
    df = pd.read_csv(p)
    missing = [c for c in FUNDING_COLS if c not in df.columns]
    if missing:
        raise DataContractError(f"{p.name} missing columns {missing}")
    df["ts"] = df["ts"].astype("int64")
    s, e = _to_ms(start), _to_ms(end)
    if s is not None:
        df = df[df["ts"] >= s]
    if e is not None:
        df = df[df["ts"] < e]
    idx = pd.to_datetime(df["ts"], unit="ms", utc=True)
    out = df.drop(columns=["ts"]).set_index(idx)
    out.index.name = "time"
    out["rate_annualized"] = out["rate"] * (24 / out["interval_hours"]) * 365
    if not quiet:
        print(f"FUNDING PREFLIGHT  {p.name}: {len(out):,} rows, "
              f"interval {out['interval_hours'].iloc[0] if len(out) else '—'}h (raw stored)",
              file=sys.stderr)
    return out
