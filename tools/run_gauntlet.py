"""Gauntlet runner: backtest a bot strategy on the real CSV store.

    python tools/run_gauntlet.py --strategy vsma_band --symbol BTC --tf 4h

Contract compliance:
  * Fills at NEXT BAR OPEN — the position decided on bar i's close is applied
    at bar i+1's open. Same-bar-close fills are look-ahead and never happen.
  * Explicit costs (taker fee + slippage bps), full run repeated at 2x costs.
  * Metrics via niceFuncs only; 24/7 annualization.
  * Monte Carlo: permutation without replacement, OOS-free data does not
    exist here — every number is labeled IS (in-sample) because the strategy
    parameters were chosen on this market/timeframe in StratSearch alpha.
  * Funding cost is NOT yet modeled (engine gap, tracked in the vault) —
    stated on the report rather than hidden.

Results print to stdout and save under data/research_results/ (local-only,
gitignored). IS numbers are triage, not evidence of an edge.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from bots.strategies import vsma_band_positions                # noqa: E402
from datadogs.common import TIMEFRAME_MS                       # noqa: E402
import niceFuncs                                               # noqa: E402

STRATEGY_POSITIONS = {
    "vsma_band": vsma_band_positions,
}

# Cost model carried over from the StratSearch beta runner (per side).
DEFAULT_FEE_BPS = 6.0       # 0.06 %
DEFAULT_SLIP_BPS = 2.0      # 0.02 %


def _trade_pnls(equity: list[float], positions: list[int]) -> list[float]:
    """Per-trade PnL (in equity units) by segmenting at position changes.
    equity[i] is sampled after positions[i-1] was held, so a trade spanning
    positions[a..b) maps to equity[a..b]."""
    pnls: list[float] = []
    start_idx = None
    prev = 0
    for i, sig in enumerate(positions):
        if sig != prev:
            if prev != 0 and start_idx is not None:
                pnls.append(equity[min(i, len(equity) - 1)] - equity[start_idx])
            start_idx = i if sig != 0 else None
            prev = sig
    if prev != 0 and start_idx is not None:
        pnls.append(equity[-1] - equity[start_idx])
    return pnls


def _run(opens, positions, fee_bps, slip_bps, tf_ms):
    equity = niceFuncs.unit_backtest(opens, positions, fee_bps=fee_bps,
                                     slippage_bps=slip_bps)
    m = niceFuncs.metrics(equity, timeframe_ms=tf_ms)
    t = niceFuncs.trade_stats(_trade_pnls(equity, list(positions)))
    return equity, {**m, **t}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strategy", default="vsma_band", choices=sorted(STRATEGY_POSITIONS))
    ap.add_argument("--symbol", default="BTC")
    ap.add_argument("--tf", default="4h", choices=sorted(TIMEFRAME_MS, key=TIMEFRAME_MS.get))
    ap.add_argument("--fee-bps", type=float, default=DEFAULT_FEE_BPS)
    ap.add_argument("--slip-bps", type=float, default=DEFAULT_SLIP_BPS)
    ap.add_argument("--mc-runs", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args(argv)
    tf_ms = TIMEFRAME_MS[a.tf]

    from data_loader.loader import load
    df = load(a.symbol, a.tf)                      # prints the preflight

    pos_fn = STRATEGY_POSITIONS[a.strategy]
    positions, _, _, _ = pos_fn(df)

    # NEXT-BAR-OPEN fills happen inside niceFuncs.unit_backtest.
    opens = df["open"].astype(float).tolist()
    pos_list = [int(p) for p in positions]

    equity, base = _run(opens, pos_list, a.fee_bps, a.slip_bps, tf_ms)
    _, stress = _run(opens, pos_list, a.fee_bps * 2, a.slip_bps * 2, tf_ms)

    rets = niceFuncs.returns_from_equity(equity)
    mc = niceFuncs.permutation_mc(rets, runs=a.mc_runs, seed=a.seed)

    # Rolling 30-day window stability (no fitting -> not walk-forward;
    # this measures whether the result is concentrated in a few windows).
    win = int(30 * 24 * 3_600_000 / tf_ms)
    window_sharpes: list[float] = []
    profitable = 0
    for s in range(0, len(equity) - win, win):
        wm = niceFuncs.metrics(equity[s:s + win + 1], timeframe_ms=tf_ms)
        if wm:
            window_sharpes.append(wm["sharpe_ann"])
            profitable += wm["return_pct"] > 0

    # Parameter plateau: +/-30% on vsma_length. atr_length is intentionally
    # absent — ATR feeds only stop/TP metadata, never entries/exits, so its
    # column would be constant by construction.
    plateau = []
    for vl in (14, 16, 18, 20, 22, 24, 26):
        p, _, _, _ = pos_fn(df, vsma_length=vl)
        _, pm = _run(opens, [int(x) for x in p], a.fee_bps, a.slip_bps, tf_ms)
        plateau.append({"vsma_length": vl,
                        "sharpe_ann": round(pm.get("sharpe_ann", 0.0), 3),
                        "return_pct": round(pm.get("return_pct", 0.0), 2),
                        "n_trades": pm.get("n_trades", 0.0)})

    report = {
        "label": "IS",
        "strategy": a.strategy,
        "symbol": a.symbol, "tf": a.tf,
        "data": {"path": df.attrs.get("path"), "rows": len(df),
                 "start": str(df.index[0]), "end": str(df.index[-1]),
                 "source": df.attrs.get("source")},
        "fill_rule": "next_bar_open",
        "costs": {"fee_bps": a.fee_bps, "slippage_bps": a.slip_bps,
                  "funding": "NOT MODELED (engine gap)"},
        "sizing": "full notional flip (engine baseline; beta used 2% risk)",
        "base": {k: round(v, 4) for k, v in base.items()},
        "stress_2x_costs": {k: round(v, 4) for k, v in stress.items()},
        "rolling_30d_windows": {
            "n": len(window_sharpes),
            "profitable": profitable,
            "sharpe_min": round(min(window_sharpes), 3) if window_sharpes else None,
            "sharpe_median": round(sorted(window_sharpes)[len(window_sharpes) // 2], 3)
            if window_sharpes else None,
        },
        "monte_carlo_permutation": {
            "runs": mc.runs, "seed": mc.seed,
            "observed_dd_pct": round(mc.observed_dd_pct, 2),
            "dd_p50_pct": round(mc.max_dd_p50_pct, 2),
            "dd_p95_pct": round(mc.max_dd_p95_pct, 2),
        },
        "plateau": plateau,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    out_dir = REPO_ROOT / "data" / "research_results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"gauntlet_{a.strategy}_{a.symbol}{a.tf}_{int(time.time())}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps({k: v for k, v in report.items() if k != "plateau"}, indent=2))
    print("\nPLATEAU (vsma_length -> sharpe_ann / return% / trades):")
    for p in plateau:
        print(f"  vsma {p['vsma_length']:>2}: {p['sharpe_ann']:+.2f}  "
              f"{p['return_pct']:+8.2f}%  {int(p['n_trades'])}")
    print(f"\nreport: {out}")
    if base.get("sharpe_ann", 0) > 3:
        print("WARNING: IS Sharpe > 3 — treat as a bug until proven otherwise.")
    print("Label: IS. Parameters were chosen on this market in StratSearch "
          "alpha; nothing here is out-of-sample evidence.")
    return 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    sys.exit(main())
