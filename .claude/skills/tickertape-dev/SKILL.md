---
name: tickertape-dev
description: Working on the TickerTape desktop app and its bot integration — UI panels, the signal/state file contracts, data-health displays, security hygiene, and the MoonDev API removal. Use this skill for ANY change inside the TickerTape repo, anything touching signals.jsonl, bot state files, the kill-switch, app panels/UX, or secrets/config handling.
---

# TickerTape Development

## Phase law
Read-only intelligence ONLY. No order placement, position management, or exchange write-scopes anywhere in the codebase this phase. If a task implies execution, surface it and stop. (Shadow/paper trading needs zero execution code — it's signals + bookkeeping.)

## Integration contract (do not improvise schemas)
- `signals/signals.jsonl` — append-only; fields per vault `04_Infrastructure/Bot-TickerTape Interface Contract.md`: `ts` (signal bar open, ms UTC), `emitted_at`, `strategy`, `version`, `symbol`, `tf`, `event`, `side`, `bar_close`, `stop`, `target`, `confidence`, `mode`, `meta`.
- `state/<bot>.json` — atomic write (temp + rename), heartbeat fields; app renders green <2 bars stale / yellow <5 / red.
- Kill-switch: existence of `state/KILL` halts every bot within one loop. Any bot loop you write must check it.
- Bots never import the app; the app never imports strategies. Files are the only bridge. Don't introduce sockets, queues, or DBs without a Decision Log entry — SQLite is the *approved future* upgrade path, not a default.

## MoonDev removal
Active migration. Never add a new MoonDev call. When touching code that uses it, flag the call sites and propose the keyless replacement (Hyperliquid info API / CCXT) — but per the ask-first rule, don't migrate unprompted.

## Security hygiene (audit-relevant areas)
- Keys: env files only (gitignored), loaded at startup, never logged, never in argv, never echoed in errors. Pattern-sanitize log output.
- Validate anything crossing a boundary: CSV rows, API responses, user-loaded strategy files (no `eval`/`exec`/`pickle.load` on user content).
- Pin dependencies; new ones require the checklist + approval.
- Real audit requires the real repo. If asked to audit code that isn't present, say exactly that and request it — never produce generic findings dressed as an audit.

## UI/UX
- Keep the existing color scheme; cyberpunk command-center direction; density over chrome (a stat-desk screen, not a marketing page).
- Every analytical panel shows its data's freshness; stale data gets a visible banner, never silent.
- Read-only phase panels in priority order: signal tape → bot health → data health → pipeline board → shadow-vs-backtest divergence.
- Persistent not-financial-advice disclaimer (core value).
- Plots/exports: dark theme, consistent with the matplotlib house style.
