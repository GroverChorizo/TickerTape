# TickerTape — Local-First Quant Research Terminal

A desktop trading-intelligence terminal for Hyperliquid markets: a Textual TUI
over a keyless, real-data-only pipeline, with a strategy shadow layer that
emits signals to local files — no orders, no execution, read-only phase.

**This is research tooling. Nothing here is financial advice.**

## Core values

- **Real data only.** No synthetic candles — not in backtests, tests, demos, or
  fallbacks. A missing CSV means "fetch it," never "simulate it."
- **Local first.** No cloud services, no telemetry. Market data comes from
  keyless public exchange APIs; everything else stays on your machine.
- **Deterministic & reproducible.** Same bars in, same answer out. Every
  number traces to a real CSV and a labeled run.
- **No live trading.** Bots run in shadow mode only: they say what they
  *would* do. There is no order or execution code in this phase.

## Architecture

```
 datadogs (ccxt, keyless) ──► data/SYMBOL-TIMEFRAME.csv ◄── data_loader.loader (THE only door)
                                        │                          │
              ┌─────────────────────────┼─────────────┐            │
              ▼                         ▼             ▼            ▼
        strategy bots             TickerTape TUI   backtesting engine
              │ append                  ▲ read
              ▼                         │
        signals/signals.jsonl ──────────┤      state/KILL = kill-switch
        state/<bot>.json ───────────────┘      (bots stop on next loop)
```

- **`datadogs/`** — keyless OHLCV + funding fetchers (Hyperliquid primary;
  Coinbase spot for deep history, always venue-tagged, never blended).
  Validates everything before writing; gaps are reported, never filled.
- **`data_loader/`** — the only sanctioned CSV reader. Prints a preflight
  (rows, range, gaps, dupes) and raises on contract violations.
- **`tui/`** — the terminal app: profile screens (Day Trader, Liquidation
  Hunter, Whale Watcher, Funding Arbitrage), Research screen (backtest jobs,
  Monte Carlo), and the Ops screen (`:ops`) — data health, signal tape,
  bot health.
- **`bots/`** — standalone shadow bots. They never import TickerTape;
  the only shared surfaces are the CSV store and the signal/state files.
- **`backtesting/`** — event-driven engine, walk-forward, Monte Carlo
  (permutation without replacement).

## Quick start

```bash
pip install -r requirements.txt
pip install -e .          # registers the `tt` / `tickertape` commands

# 1. Verify the data pipeline against live exchanges (~2 min)
python -m datadogs selftest

# 2. Stand up the data store (real bars, keyless)
python -m datadogs fetch-all
python -m datadogs backfill BTC 4h --days 900
python -m datadogs funding BTC --venue hyperliquid --days 90
python -m datadogs health

# 3. Launch
tt                       # or `tickertape` (terminal UI; same as python -m tui.app)
tt serve                 # serve the UI as a local desktop/web app (http://127.0.0.1:8000)
```

Core market data (price, funding, open interest, orderbook, candles) is
**keyless** via the Hyperliquid info API. The opt-in intel panels (whales,
liquidations, smart-money, events) need a MoonDev key — set `MOONDEV_API_KEY`
in your secrets file and `:reload`; without it they show "not configured" and
everything else runs normally.

Schedule `python -m datadogs fetch-all` every 15 minutes (Task Scheduler /
cron) and the store maintains itself; `health` exits 1 on any STALE/ERROR so
it can gate anything.

## Shadow bots

The baseline strategy is **VSMA Band** (`bots/strategies.py`), ported from the
StratSearch beta tier where it passed the alpha gate on BTC 4H. Run it:

```bash
python -m bots.runner --strategy vsma_band --symbol BTC --tf 4h
```

- Signals append to `signals/signals.jsonl` (one JSON object per line);
  heartbeats write atomically to `state/<bot_id>.json`.
- Kill switch: create `state/KILL` — every bot exits cleanly on its next loop.
- Watch it live in the TUI: `:ops` → Signal Tape / Bot Health.
- Status vocabulary is controlled: code is `untested → runs →
  shadow-verified → gauntlet-passed`. Alpha-stage performance numbers are
  in-sample triage only; nothing is promoted without out-of-sample validation
  (walk-forward ≥8 windows, Monte Carlo, parameter plateau).

## Verification gates

All four must pass before a change is done:

```bash
python tools/release_gate.py     # pytest + ruff + mypy + data integrity gate
```

## Data contract (summary)

- Files: `data/SYMBOL-TIMEFRAME.csv` (e.g. `BTC-15m.csv`), columns
  `ts,open,high,low,close,volume`; `ts` = bar open, epoch ms UTC, strictly
  increasing, closed bars only. Venue-tagged research files
  (`BTC.coinbase-15m.csv`) keep exchanges separate — different venues have
  different liquidity and are never mixed in one series.
- Funding stored raw with its interval (Hyperliquid hourly); annualized at
  display only.
- All loading goes through `data_loader.loader.load()` /
  `load_funding()` — nothing else reads price CSVs.

## Secrets & local configuration 🔐

- Canonical secrets file (created on first run):
  - POSIX: `~/.tickertape/secrets/HLdontShare.env`
  - Windows: `%USERPROFILE%\.tickertape\secrets\HLdontShare.env`
  - In-app: `:secrets` opens it in your editor.
- Overrides: `TICKERTAPE_SECRETS_PATH` or `HL_DONT_SHARE_PATH`.
- Market data needs **no keys** — the secrets file exists for future
  authenticated features. Never commit secrets; logging is sanitized.

## Support the project

If you find this project useful, you may support its continued development via
GitHub Sponsors, one-time donations (BTC, XMR), or contributions and feedback.
Donations do not grant any special rights or commercial license.

## Licensing

This project is licensed under the GNU Affero General Public License v3.0
(AGPL-3.0).

Commercial licenses are available for entities wishing to:
- embed this software in proprietary systems
- offer it as part of a commercial service
- distribute modified versions without open-sourcing changes

For commercial licensing inquiries, contact: elias@osgrovesolutions.com
