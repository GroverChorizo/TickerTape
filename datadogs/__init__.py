"""datadogs v2 — keyless, MoonDev-free market data layer.

Venues via ccxt public endpoints (no API keys for market data):
  hyperliquid (perps + funding), binance (spot), binance_perp (USDM + funding),
  coinbase (spot, via the Exchange API).

Contract: data/SYMBOL-TIMEFRAME.csv · ts,open,high,low,close,volume ·
ts = bar OPEN time, epoch milliseconds, UTC, closed bars only.

Status: offline-verified (compiles, CLI, validator logic). Live paths are
`untested` until `python -m datadogs selftest` passes on a networked machine.
"""

__version__ = "2.0.0"
SOURCE_TAG = f"datadogs v{__version__} (ccxt)"
