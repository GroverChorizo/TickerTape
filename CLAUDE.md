# CLAUDE.md — TickerTape / Quant Brain

You are working on Grover's quantitative trading system: **TickerTape** (desktop trading-intelligence app, read-only phase) plus a strategy pipeline (research → backtest → shadow → paper → live). Local-first, real-data-only, institutional rigor. The canonical knowledge base is the Obsidian **Quant Brain** vault; this file is its enforcement arm inside the repo.

## HARD RULES — violations void the session

1. **REAL DATA ONLY.** Never generate synthetic, sample, demo, mock, or "realistic" price data — not in backtests, tests, examples, or fallbacks. No `np.random` near prices, ever. If a CSV is missing: stop and say so; the fix is fetching real data, never simulating it. (This rule exists because a synthetic-data incident voided the entire v1 strategy library in Feb 2026.)
2. **ASK BEFORE EDITING CODE.** Propose the change and the diff scope first; wait for approval. Surgical diffs, never wholesale rewrites. Deletions ship alone with grep evidence of zero callers.
3. **LOCAL FIRST.** No cloud services, telemetry, or remote storage for data/state. No new dependencies without running the dependency checklist (cost / key / rate limits / maintenance / exit plan) and getting approval.
4. **SECRETS.** Keys live in env files only. Never print, log, or commit them. Logging is sanitized.
5. **CONTROLLED STATUS VOCABULARY.** Code is exactly one of: `untested` → `runs` → `shadow-verified` → `gauntlet-passed`. Banned phrases: "production ready," "100% complete," "this will give you an edge," and any performance claim not backed by a labeled OOS report. No hype, no rocket emojis on status claims.
6. **SHOW REAL OUTPUT.** Never describe results of code you didn't run. Paste actual run output or say it's untested.

## Data contract

- Files: `data/SYMBOL-TIMEFRAME.csv` (e.g. `BTC-15m.csv`). Columns `ts,open,high,low,close,volume` (+optional `trades,funding`). `ts` = bar open, **epoch ms, UTC**, strictly increasing.
- **All loading goes through `data_loader/loader.py`** — strategy/app code never reads CSVs directly.
- Before coding against any file: print the preflight (path, rows, date range, gaps, dupes). Never invent column names from memory.
- Gaps are reported, never silently forward-filled. Funding stored raw with its interval (Hyperliquid hourly, Binance 8h); annualize at display only.

## Backtest contract

- Engine: the custom event-driven engine. Shared math lives in `niceFuncs` (used by backtest AND live — keep it that way; it's what makes shadow-diffing possible).
- Fills: **next bar open** after signal-bar close. Same-bar-close fills are look-ahead → auto-reject.
- Costs always explicit: taker fee + vol-scaled slippage + real funding series. Every gauntlet run repeated at 2× costs.
- Validation: rolling walk-forward (6mo train / 1mo test) ≥8 windows; purged+embargoed CV for fitted components; Monte Carlo = **permutation without replacement** (bootstrap-with-replacement caused a real bug here), 1,000 runs, OOS trades only; parameter plateau ±30%.
- Metrics via `niceFuncs.metrics()` only; label every number IS / WF / OOS. 24/7 annualization (15m → 35,040 bars/yr). OOS Sharpe > 3 = treat as a bug.
- Promotion thresholds live in the vault: `01_Pipeline/B - Validation Gauntlet.md`.

## Architecture boundaries

- Bots ↔ app communicate ONLY via local files: append-only `signals/signals.jsonl`, atomic `state/<bot>.json`, kill-switch = existence of `state/KILL` (checked every loop). Bots never import TickerTape; TickerTape never imports strategies. Schema: vault `04_Infrastructure/Bot-TickerTape Interface Contract.md`.
- No execution/order code in the read-only phase. MEXC futures is institutional-only — never target it for live perps.
- UI: keep the existing color scheme; cyberpunk command-center aesthetic; dark-theme matplotlib for all plots. Visible not-financial-advice disclaimer.

## Session protocol

- **First move every session:** verify inputs exist (`ls` the repo/data/uploads). No artifact → the task becomes acquiring it. Never produce review-shaped output about code you can't see.
- When Grover says **"rules check"**: stop, re-read this file, restate the active constraints, then continue.
- End significant sessions with a handoff: done (with status vocab) / in flight / blocked / first move next time.
- If two guardrail violations occur in one session, recommend ending the session and starting fresh with the handoff.

Skills available in `.claude/skills/`: `market-data`, `backtest-validation`, `strategy-research`, `tickertape-dev`. Consult them before touching their domains.
