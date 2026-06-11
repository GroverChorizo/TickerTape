"""Command line:  python -m datadogs <command>

  fetch SYMBOL TF [--venue V] [--days N] [--tag-venue]   incremental update
  fetch-all [--days N]                                    universe sweep (scheduler entry)
  backfill SYMBOL TF --days N [--venue V] [--tag-venue]   deep history pull
  funding SYMBOL [--venue hyperliquid|binance_perp] [--days N]
  health                                                  freshness/gap table for data/
  selftest [--venue V]                                    live acceptance test

Exit codes: 0 ok · 1 validation/selftest failure · 2 usage error.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

from .common import (TIMEFRAME_MS, DataContractError, iso, now_ms, read_csv,
                     read_meta, validate)
from .config import UNIVERSE, VENUES, data_dir


def _lock(timeout_s: int = 600):
    """Skip-if-running guard for fetch-all so overlapping scheduled runs never
    race on the same files. Stale locks (crashed run) are overridden."""
    lp = data_dir() / ".datadogs.lock"
    if lp.exists() and (time.time() - lp.stat().st_mtime) < timeout_s:
        print(f"another datadogs run holds {lp} (age "
              f"{int(time.time() - lp.stat().st_mtime)}s) — skipping", file=sys.stderr)
        sys.exit(0)
    lp.write_text(str(os.getpid()))
    return lp


def cmd_fetch(a) -> int:
    from .fetch import incremental_update
    incremental_update(a.symbol, a.timeframe, a.venue, days=a.days,
                       tag_venue=a.tag_venue)
    return 0


def cmd_fetch_all(a) -> int:
    from .fetch import fetch_all
    lock = _lock()
    try:
        reps = fetch_all(days=a.days)
        return 0 if all(r.ok for r in reps) else 1
    finally:
        lock.unlink(missing_ok=True)


def cmd_backfill(a) -> int:
    from .fetch import incremental_update
    incremental_update(a.symbol, a.timeframe, a.venue, days=a.days,
                       tag_venue=a.tag_venue)
    return 0


def cmd_funding(a) -> int:
    from .fetch import fetch_funding
    fetch_funding(a.symbol, a.venue, days=a.days)
    return 0


def cmd_health(a) -> int:
    """Freshness/integrity table — this is what TickerTape's data-health panel reads."""
    rows, worst = [], 0
    for p in sorted(data_dir().glob("*.csv")):
        if p.name.endswith("-funding.csv"):
            continue
        try:
            stem = p.stem                       # BTC-15m  or  BTC.hyperliquid-15m
            sym, tfname = stem.rsplit("-", 1)
            if tfname not in TIMEFRAME_MS:
                continue
            df = read_csv(p)
            rep = validate(df, tfname, path=str(p), source=read_meta(p).get("source", ""))
            age_bars = (now_ms() - rep.ts_max) / TIMEFRAME_MS[tfname] if rep.rows else float("inf")
            if not rep.ok:
                status, worst = "ERROR", max(worst, 1)
            elif age_bars > 2:
                status, worst = "STALE", max(worst, 1)
            else:
                status = "OK"
            rows.append((p.name, f"{rep.rows:,}", f"{age_bars:.1f}", str(len(rep.gaps)),
                         iso(rep.ts_max) if rep.rows else "—", status))
        except Exception as e:  # a broken file must show up, not crash the table
            rows.append((p.name, "—", "—", "—", "—", f"ERROR {e}"))
            worst = max(worst, 1)
    if not rows:
        print(f"no OHLCV csv files in {data_dir()} — run: python -m datadogs fetch-all")
        return 0
    hdr = ("file", "rows", "age(bars)", "gaps", "last bar (UTC)", "status")
    w = [max(len(hdr[i]), *(len(r[i]) for r in rows)) for i in range(6)]
    line = "  ".join(h.ljust(w[i]) for i, h in enumerate(hdr))
    print(line + "\n" + "-" * len(line))
    for r in rows:
        print("  ".join(str(r[i]).ljust(w[i]) for i in range(6)))
    return worst


def cmd_selftest(a) -> int:
    from .selftest import main as st
    return st([a.venue] if a.venue else None)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="datadogs", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, days_default=None):
        sp.add_argument("symbol", help=f"base symbol, e.g. BTC (universe: {', '.join(UNIVERSE)})")
        sp.add_argument("timeframe", choices=sorted(TIMEFRAME_MS, key=TIMEFRAME_MS.get))
        sp.add_argument("--venue", choices=list(VENUES), default=None,
                        help="default = primary venue from config.UNIVERSE")
        sp.add_argument("--days", type=int, default=days_default,
                        help="lookback when no file exists yet")
        sp.add_argument("--tag-venue", action="store_true",
                        help="write SYMBOL.VENUE-TF.csv (multi-venue research)")

    common(sub.add_parser("fetch", help="incremental update of one market"))
    sp = sub.add_parser("backfill", help="deep history pull for a new market")
    common(sp)
    sp.set_defaults(days=365)
    sp = sub.add_parser("fetch-all", help="incremental update of the whole universe")
    sp.add_argument("--days", type=int, default=None)
    sp = sub.add_parser("funding", help="raw funding-rate history (perp venues)")
    sp.add_argument("symbol")
    sp.add_argument("--venue", default="hyperliquid")
    sp.add_argument("--days", type=int, default=30)
    sub.add_parser("health", help="freshness/integrity table for the CSV store")
    sp = sub.add_parser("selftest", help="LIVE acceptance test (network required)")
    sp.add_argument("--venue", choices=list(VENUES), default=None)
    return p


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    handlers = {"fetch": cmd_fetch, "fetch-all": cmd_fetch_all, "backfill": cmd_backfill,
                "funding": cmd_funding, "health": cmd_health, "selftest": cmd_selftest}
    try:
        return handlers[a.cmd](a)
    except DataContractError as e:
        print(f"\nDATA CONTRACT ERROR: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
