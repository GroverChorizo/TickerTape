"""Configuration: trading universe, timeframes, venue specifications.

Edit UNIVERSE/TIMEFRAMES to taste. Everything else should rarely change.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# ── Universe ──────────────────────────────────────────────────────────────
# symbol -> primary venue. Default filename stays SYMBOL-TIMEFRAME.csv and is
# always written from the PRIMARY venue, so existing loader/strategy code keeps
# working. Cross-venue research files use --tag-venue (SYMBOL.VENUE-TF.csv).
UNIVERSE: dict[str, str] = {
    "BTC": "hyperliquid",
    "ETH": "hyperliquid",
    "SOL": "hyperliquid",
}

TIMEFRAMES: list[str] = ["5m", "15m", "1h", "4h"]  # 1h/4h = VSMA Band timeframes

DEFAULT_BACKFILL_DAYS = 30  # first-ever fetch reaches back this far unless --days given


# ── Venues ────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class VenueSpec:
    ccxt_id: str            # ccxt exchange class
    symbol_tpl: str         # "{base}" -> ccxt unified symbol
    page_limit: int         # candles per request (venue cap, conservative)
    market_kind: str        # "spot" | "perp"
    funding_interval_h: int | None  # None = venue has no funding (spot)


VENUES: dict[str, VenueSpec] = {
    # Hyperliquid perps — keyless info API, hourly funding.
    "hyperliquid": VenueSpec("hyperliquid", "{base}/USDC:USDC", 1000, "perp", 1),
    # Binance spot — public klines, no key.
    "binance": VenueSpec("binance", "{base}/USDT", 1000, "spot", None),
    # Binance USDⓈ-M perps — public klines + 8h funding, no key for market data.
    "binance_perp": VenueSpec("binanceusdm", "{base}/USDT:USDT", 1000, "perp", 8),
    # Coinbase Exchange spot — public candles, 300/page cap.
    "coinbase": VenueSpec("coinbaseexchange", "{base}/USD", 300, "spot", None),
}

# Venues that can serve funding history. `funding binance ...` auto-routes to
# binance_perp (funding is a perp concept; spot has none).
FUNDING_VENUES = {"hyperliquid", "binance_perp"}
FUNDING_ALIAS = {"binance": "binance_perp"}

# NOTE (pre-mortem §E): MEXC futures is institutional-only — intentionally absent.
# NOTE: ccxt unified symbols above are the documented conventions; `selftest`
# confirms them against live markets before you trust the pipeline.


# ── Paths ─────────────────────────────────────────────────────────────────
def data_dir() -> Path:
    """Resolve the CSV store. Override with env QB_DATA_DIR; default ./data."""
    d = Path(os.environ.get("QB_DATA_DIR", "data"))
    d.mkdir(parents=True, exist_ok=True)
    return d
