"""Keyless fetchers (ccxt public endpoints). Replaces the MoonDev data layer.

Design rules:
  * Only CLOSED bars are ever stored (the still-forming candle is dropped).
  * Validate the merged frame BEFORE writing — garbage never reaches disk.
  * Append-only + idempotent: re-running never duplicates or rewrites history.
  * No API keys touched anywhere in this module.
"""
from __future__ import annotations

import sys

import ccxt
import pandas as pd

from . import SOURCE_TAG
from .common import (CONTRACT_COLS, FUNDING_COLS, TIMEFRAME_MS, DataContractError,
                     ValidationReport, csv_path, funding_path, merge_frames,
                     read_csv, validate, write_atomic)
from .config import (DEFAULT_BACKFILL_DAYS, FUNDING_ALIAS, FUNDING_VENUES,
                     TIMEFRAMES, UNIVERSE, VENUES, VenueSpec)

MAX_PAGES = 5000  # hard stop ≈ years of 15m bars; prevents runaway loops

_exchanges: dict[str, ccxt.Exchange] = {}


def get_exchange(venue: str) -> ccxt.Exchange:
    if venue not in VENUES:
        raise ValueError(f"unknown venue '{venue}' (have: {', '.join(VENUES)})")
    if venue not in _exchanges:
        spec = VENUES[venue]
        _exchanges[venue] = getattr(ccxt, spec.ccxt_id)({"enableRateLimit": True})
    return _exchanges[venue]


def unified_symbol(venue: str, base: str) -> str:
    return VENUES[venue].symbol_tpl.format(base=base.upper())


# ── OHLCV ─────────────────────────────────────────────────────────────────
def fetch_ohlcv_df(venue: str, base: str, timeframe: str, since_ms: int,
                   until_ms: int | None = None, verbose: bool = True) -> pd.DataFrame:
    """Paginated pull of CLOSED candles in [since_ms, until_ms). Contract frame out."""
    if timeframe not in TIMEFRAME_MS:
        raise ValueError(f"unsupported timeframe '{timeframe}'")
    spec: VenueSpec = VENUES[venue]
    ex = get_exchange(venue)
    sym = unified_symbol(venue, base)
    tf = TIMEFRAME_MS[timeframe]
    until = until_ms if until_ms is not None else ex.milliseconds()

    rows: list[list] = []
    cursor, last_seen, pages = int(since_ms), None, 0
    while cursor < until and pages < MAX_PAGES:
        batch = ex.fetch_ohlcv(sym, timeframe, since=cursor, limit=spec.page_limit)
        if not batch:
            break
        tail = batch[-1][0]
        if last_seen is not None and tail <= last_seen:   # venue repeating itself
            break
        rows.extend(batch)
        last_seen = tail
        cursor = tail + tf
        pages += 1
        if verbose:
            print(f"\r  {venue}:{sym} {timeframe}  pages={pages} rows={len(rows)}",
                  end="", file=sys.stderr)
    if verbose and pages:
        print(file=sys.stderr)

    if not rows:
        return pd.DataFrame(columns=CONTRACT_COLS)

    df = pd.DataFrame(rows, columns=CONTRACT_COLS)
    df["ts"] = df["ts"].astype("int64")
    for c in CONTRACT_COLS[1:]:
        df[c] = df[c].astype(float)
    df = df[df["ts"] >= int(since_ms)]                 # some venues round down
    df = df[df["ts"] + tf <= ex.milliseconds()]        # closed bars only
    df = (df.sort_values("ts").drop_duplicates("ts", keep="last")
            .reset_index(drop=True))
    return df


def incremental_update(base: str, timeframe: str, venue: str | None = None,
                       days: int | None = None, tag_venue: bool = False,
                       verbose: bool = True) -> ValidationReport:
    """Fetch new closed bars since the file's last row (or `days` back if new),
    validate the MERGED result, then atomically write. Idempotent."""
    base = base.upper()
    venue = venue or UNIVERSE.get(base)
    if venue is None:
        raise ValueError(f"{base} has no primary venue in config.UNIVERSE — pass --venue")
    tf = TIMEFRAME_MS[timeframe]
    path = csv_path(base, timeframe, venue if tag_venue else None)

    existing = read_csv(path)
    if len(existing):
        since = int(existing["ts"].max()) + tf
    else:
        lookback = (days or DEFAULT_BACKFILL_DAYS) * 86_400_000
        since = get_exchange(venue).milliseconds() - lookback

    new = fetch_ohlcv_df(venue, base, timeframe, since, verbose=verbose)
    merged = merge_frames(existing, new) if len(new) else existing

    rep = validate(merged, timeframe, path=str(path), source=f"{SOURCE_TAG} · {venue}")
    if not rep.ok:
        print(rep.preflight(), file=sys.stderr)
        raise DataContractError(f"validation failed for {path.name} — nothing written")

    if len(new):
        write_atomic(merged, path, meta={"source": SOURCE_TAG, "venue": venue,
                                         "symbol": base, "timeframe": timeframe,
                                         "kind": VENUES[venue].market_kind})
    if verbose:
        print(rep.preflight())
        if not len(new):
            print(f"  status:      up to date (no new closed {timeframe} bars)")
    return rep


def fetch_all(days: int | None = None, verbose: bool = True) -> list[ValidationReport]:
    """Universe × timeframes sweep (the scheduler entry point)."""
    reports = []
    for base, venue in UNIVERSE.items():
        for tfname in TIMEFRAMES:
            reports.append(incremental_update(base, tfname, venue, days=days,
                                              verbose=verbose))
    return reports


# ── Funding ───────────────────────────────────────────────────────────────
def fetch_funding(base: str, venue: str = "hyperliquid", days: int = 30,
                  verbose: bool = True) -> pd.DataFrame:
    """Pull raw funding-rate history. Stored as published with its interval —
    annualize at display time only (Hyperliquid=1h, Binance perp=8h)."""
    base = base.upper()
    venue = FUNDING_ALIAS.get(venue, venue)
    if venue not in FUNDING_VENUES:
        raise ValueError(f"venue '{venue}' has no funding (spot). Use one of: "
                         f"{', '.join(sorted(FUNDING_VENUES))}")
    spec = VENUES[venue]
    ex = get_exchange(venue)
    sym = unified_symbol(venue, base)
    since = ex.milliseconds() - days * 86_400_000

    rows, cursor, last_seen, pages = [], since, None, 0
    while pages < MAX_PAGES:
        batch = ex.fetch_funding_rate_history(sym, since=cursor, limit=500)
        if not batch:
            break
        tail = batch[-1]["timestamp"]
        if last_seen is not None and tail <= last_seen:
            break
        rows.extend(batch)
        last_seen, cursor, pages = tail, tail + 1, pages + 1

    if not rows:
        return pd.DataFrame(columns=FUNDING_COLS)

    df = pd.DataFrame({
        "ts": [int(r["timestamp"]) for r in rows],
        "rate": [float(r["fundingRate"]) for r in rows],
        "interval_hours": spec.funding_interval_h,
    }).sort_values("ts").drop_duplicates("ts", keep="last").reset_index(drop=True)

    path = funding_path(base, venue)
    prev = read_csv(path)
    if len(prev):
        df = (pd.concat([prev[FUNDING_COLS], df], ignore_index=True)
                .sort_values("ts").drop_duplicates("ts", keep="last")
                .reset_index(drop=True))
    write_atomic(df, path, meta={"source": SOURCE_TAG, "venue": venue,
                                 "symbol": base, "kind": "funding",
                                 "interval_hours": spec.funding_interval_h})
    if verbose:
        print(f"  funding {base} @ {venue}: {len(df):,} rows "
              f"(interval {spec.funding_interval_h}h, stored raw)")
    return df
