"""Live acceptance test — run ON YOUR MACHINE (network required):

    python -m datadogs selftest            # all venues
    python -m datadogs selftest --venue hyperliquid

Constitution-compliant by construction: every check is anchored to candles
fetched live from the venue moments earlier. The corruption probes mutate
COPIES of that real data in memory to prove the validator rejects each
failure mode — nothing synthetic is generated, nothing fake touches disk.

Exit code 0 = the pipeline is trustworthy end-to-end (fetch → validate →
write → load round-trip). Anything else = do not point strategies at it yet.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

from .common import TIMEFRAME_MS, validate, write_atomic
from .config import FUNDING_VENUES, VENUES
from .fetch import fetch_funding, fetch_ohlcv_df, get_exchange, unified_symbol

TF = "15m"
N_BARS = 200
BASE = "BTC"


def _check(name: str, ok: bool, detail: str = "") -> bool:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    return ok


def run_venue(venue: str) -> bool:
    spec = VENUES[venue]
    print(f"\n── {venue} ({spec.ccxt_id}, {spec.market_kind}) ──")
    ok_all = True
    tf = TIMEFRAME_MS[TF]

    # 1. live fetch of real closed candles
    try:
        ex = get_exchange(venue)
        since = ex.milliseconds() - (N_BARS + 10) * tf
        df = fetch_ohlcv_df(venue, BASE, TF, since, verbose=False)
        sym = unified_symbol(venue, BASE)
        ok_all &= _check(f"live fetch {sym} {TF}", len(df) >= N_BARS // 2,
                         f"{len(df)} closed bars")
        if len(df) == 0:
            return False
    except Exception as e:
        return _check("live fetch", False, repr(e))

    # 2. real data passes the contract
    rep = validate(df, TF, path=f"<live:{venue}>", source="selftest")
    ok_all &= _check("contract validation on live data", rep.ok,
                     "; ".join(rep.errors) if rep.errors else f"{rep.rows} rows clean")

    # 3. corruption probes — mutated COPIES of the real frame must be rejected
    probes = []
    c1 = df.copy()
    c1.loc[len(c1)] = c1.iloc[-1]                                     # duplicate ts
    probes.append(("rejects duplicate timestamps", c1,
                   lambda r: any("duplicate" in e for e in r.errors)))
    c2 = df.copy()
    c2.loc[c2.index[len(c2) // 2], "low"] = float(c2["high"].max()) * 2
    probes.append(("rejects low>high corruption", c2,
                   lambda r: any("low ≤" in e for e in r.errors)))
    c3 = df.copy()
    c3["ts"] = c3["ts"] // 1000                                       # seconds-unit
    probes.append(("rejects seconds-unit timestamps", c3,
                   lambda r: any("epoch-milliseconds" in e for e in r.errors)))
    c4 = df.copy()
    c4 = c4.drop(c4.index[50:53])                                     # 3-bar hole
    probes.append(("reports (not fills) a 3-bar gap", c4,
                   lambda r: r.ok and any(n == 3 for _, _, n in r.gaps)))
    for name, frame, expect in probes:
        r = validate(frame.reset_index(drop=True), TF, path="<probe>")
        ok_all &= _check(name, expect(r),
                         "; ".join(r.errors[:1]) or f"gaps={[(g[2]) for g in r.gaps]}")

    # 4. disk round-trip with the REAL frame
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / f"{BASE}-{TF}.csv"
        write_atomic(df, p, meta={"source": "selftest", "venue": venue,
                                  "symbol": BASE, "timeframe": TF})
        back = __import__("pandas").read_csv(p)
        same_ts = (back["ts"].astype("int64").to_numpy() == df["ts"].to_numpy()).all()
        same_px = np.allclose(back[["open", "high", "low", "close", "volume"]].to_numpy(),
                              df[["open", "high", "low", "close", "volume"]].to_numpy(),
                              rtol=0, atol=1e-9)
        ok_all &= _check("atomic write → read round-trip", bool(same_ts and same_px))

    # 5. funding (perp venues only)
    if venue in FUNDING_VENUES:
        try:
            f = fetch_funding(BASE, venue, days=5, verbose=False)
            ok_all &= _check("funding history fetch", len(f) > 0 and
                             np.isfinite(f["rate"]).all(),
                             f"{len(f)} rows @ {spec.funding_interval_h}h interval")
        except Exception as e:
            ok_all &= _check("funding history fetch", False, repr(e))
    return ok_all


def main(venues: list[str] | None = None) -> int:
    targets = venues or list(VENUES)
    print("datadogs selftest — every check anchored to LIVE exchange data; "
          "no synthetic series, nothing fake written to disk.")
    results = {v: run_venue(v) for v in targets}
    print("\n── summary ──")
    for v, ok in results.items():
        print(f"  {v:14s} {'PASS' if ok else 'FAIL'}")
    all_ok = all(results.values())
    print("\npipeline status:", "trustworthy — point the loader at it"
          if all_ok else "NOT trustworthy — fix failures before any strategy reads this data")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
