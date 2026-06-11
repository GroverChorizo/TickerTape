---
name: market-data
description: Fetching, validating, and loading market data for Grover's trading system. Use this skill whenever a task touches CSVs in data/, the datadog scripts (BinanceDataDog, hypeDatadog, cbDataDog), loader.py, Hyperliquid/CCXT/exchange APIs, funding rates, backfills, or ANY situation where price data is needed and might be missing — especially before writing code that reads OHLCV, and especially if tempted to create sample or placeholder data (never do that; use this skill instead).
---

# Market Data

## Prime directive
Real data only. If the file isn't there, the deliverable changes from "the analysis" to "the fetch." Synthetic/sample/demo price data is prohibited in every context including unit tests (tests use small *real* CSV slices checked into `tests/fixtures/`).

## File contract
`data/SYMBOL-TIMEFRAME.csv` · columns `ts,open,high,low,close,volume[,trades,funding]` · `ts` = bar open, epoch **ms**, **UTC**, strictly increasing, no dupes. One market × one timeframe per file.

## Loading
Only through `data_loader/loader.py`. It must (and if it doesn't yet, propose adding):
1. assert ms-unit timestamps (reject seconds: any ts < 10^12 for modern data → fail loudly)
2. assert monotonic, deduped index; return tz-aware UTC DataFrame
3. report gaps > 1 bar (never auto-fill) and OHLC sanity (`low ≤ open,close ≤ high`, vol ≥ 0)
4. print the preflight block (path, rows, range, gaps, dupes, source)

Paste the preflight into your response before any code that consumes the data.

## Fetching (keyless-first)
- **Hyperliquid info API** — free, no key: candles, funding (hourly interval), liquidations, meta. Verify current endpoint shapes against live docs in-session; do not trust memorized schemas.
- **CCXT** for Binance/Coinbase spot+perp OHLCV (`fetch_ohlcv`, public, keyless). Respect rate limits via ccxt's built-in throttle.
- **yfinance** — equities/commodities only, and only after crypto is end-to-end (sequencing rule).
- Writes are append-only and idempotent: dedupe on `ts` before save; never rewrite history.
- New source? Run the dependency checklist (cost/key/limits/maintenance/exit) and ask before adding. The MoonDev API is being removed — never add new code paths that call it.

## Funding rates
Store the raw per-interval rate exactly as published plus an `interval` column. Hyperliquid = 1h, Binance = 8h. Positive = longs pay shorts. Annualize only at display/analysis time. Mixing intervals or pre-annualizing in storage is a known trap.

## Backfill procedure (new symbol/timeframe)
max history pull → loader validation → cross-check one overlapping week against a second source (median |Δclose| > 5 bps → stop and investigate) → commit → register in TickerTape data-health.
