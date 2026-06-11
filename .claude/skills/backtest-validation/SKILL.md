---
name: backtest-validation
description: Running and validating strategy backtests to Grover's gauntlet standard. Use this skill for ANY task involving backtesting, strategy performance, Sharpe/Sortino/Calmar/drawdown metrics, walk-forward or cross-validation, Monte Carlo simulation, parameter optimization, or whenever asked "does this strategy work" — and use it BEFORE reporting any performance number, even informally.
---

# Backtest & Validation

## Engine rules
- Custom **event-driven** engine for any number used in a decision; vectorized pandas only for quick triage (label triage output as such).
- Shared math in `niceFuncs` — one implementation serving backtest and live. Never fork indicator/sizing/metric logic into a strategy file.
- Data via `loader.py` only; preflight block printed (see market-data skill).

## Anti-look-ahead checklist (run mentally on every diff)
- [ ] Fill = **next bar open** after the signal bar closes. Same-bar-close fill → reject.
- [ ] All `shift()` directions verified with a 3-row hand trace pasted in the response.
- [ ] Indicators have explicit warmup; no full-series fitting (scalers, percentiles, parameters) before the train/test split.
- [ ] HTF data derived by resampling inside the engine, never from a separately-loaded file.
- [ ] No use of `high`/`low` of the entry bar for same-bar stop/target resolution without a conservative intra-bar rule (assume worst order: stop before target when both touch).

## Cost model (always explicit, in config)
taker fee (venue-real, default 5 bps/side) + slippage (2 bps + 0.1×ATR14/price) + **real funding series** for perps. Sizing: fixed-fractional 1% risk. Every gauntlet result also reported at **2× costs**.

## Validation gauntlet (gate G2 — what "validated" means)
1. **Walk-forward**: rolling 6mo train / 1mo test, ≥8 windows, params fit on train only. Degradation = OOS/IS Sharpe; <0.3 = overfit.
2. **Purged & embargoed CV** (López de Prado) if anything is fitted/ML: purge label-overlap, ~1-day embargo.
3. **Monte Carlo**: 1,000 **permutations without replacement** of OOS trades only. (Bootstrap-with-replacement inflated results here once — it duplicates outlier wins. Never use it for this.) Report 5/50/95 pct equity, maxDD, Sharpe; rerun at 1.5× and 2× costs.
4. **Parameter plateau**: ±30% heatmap; spike = curve fit.
5. **Regime split**: trend/chop (ADX14>25) — performance must match the strategy's stated story.

Thresholds (OOS, net 1× costs): Sharpe ≥1.0 · degradation ≥0.5 · PF ≥1.3 · maxDD ≤20% · ≥100 trades · MC 5th-pct equity > start · survives 2× costs at Sharpe ≥0.5.

## Reporting discipline
- Every number labeled **IS / WF / OOS**. Unlabeled numbers are void.
- `niceFuncs.metrics()` only. 24/7 annualization (15m → 35,040 bars/yr — never 252).
- **Sanity tripwires**: OOS Sharpe >3 ⇒ assume leak/bug; PF on n<50 ⇒ refuse to headline it; equity curve too smooth ⇒ audit fills.
- An OOS window, once used for a decision, is **burned** for that strategy family — say so in the report.
- Plots: dark matplotlib — equity(log)+DD, trade scatter, rolling 90d Sharpe, MC fan.
- Verdict vocabulary: pass / fail / revision-1 against the thresholds, row by row. Never "looks great" or "production ready."
