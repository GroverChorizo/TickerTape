"""Endpoint-key registry for data feeds.

ENDPOINT_SPECS is the catalog of endpoint keys that feeds may request and
the allowlist that `tests/feeds/test_profile_feed_contracts.py` validates
profile contracts against. The path templates document the legacy data-layer
shape; URL construction now happens in `backend.network.NetworkClient`
(direct Hyperliquid) and unmapped keys surface as honest feed error states
until each panel is migrated to the local datadogs store.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class EndpointSpec:
    path: str
    symbol_case: str | None = None
    ticker_case: str | None = None
    dex_case: str | None = None
    duration_case: str | None = None
    timeframe_case: str | None = None


ENDPOINT_SPECS: Dict[str, EndpointSpec] = {
    "health": EndpointSpec("/health"),
    "prices": EndpointSpec("/api/prices"),
    "price": EndpointSpec("/api/price/{symbol}", symbol_case="upper"),
    "orderbook": EndpointSpec("/api/orderbook/{symbol}", symbol_case="upper"),
    "account": EndpointSpec("/api/account/{address}"),
    "fills": EndpointSpec("/api/fills/{address}"),
    "candles": EndpointSpec("/api/candles/{symbol}", symbol_case="upper"),
    "ticks_latest": EndpointSpec("/api/ticks/latest.json"),
    "ticks_symbol": EndpointSpec("/api/ticks/{symbol}.json", symbol_case="lower"),
    "ticks_symbol_duration": EndpointSpec(
        "/api/ticks/{symbol}_{duration}.json", symbol_case="lower", duration_case="lower"
    ),
    "ticks_stats": EndpointSpec("/api/ticks/stats.json"),
    "trades": EndpointSpec("/api/trades.json"),
    "large_trades": EndpointSpec("/api/large_trades.json"),
    "orderflow": EndpointSpec("/api/orderflow.json"),
    "orderflow_stats": EndpointSpec("/api/orderflow/stats.json"),
    "imbalance": EndpointSpec("/api/imbalance/{duration}.json", duration_case="lower"),
    "binance_funding": EndpointSpec("/api/binance_funding.json"),
    "liquidations_stats": EndpointSpec("/api/liquidations/stats.json"),
    "liquidations_scan_summary": EndpointSpec("/api/liquidations/scan_summary.json"),
    "liquidations": EndpointSpec(
        "/api/liquidations/{timeframe}.json", timeframe_case="lower"
    ),
    "hip3_liquidations_stats": EndpointSpec("/api/hip3_liquidations/stats.json"),
    "hip3_liquidations": EndpointSpec(
        "/api/hip3_liquidations/{timeframe}.json", timeframe_case="lower"
    ),
    "all_liquidations_stats": EndpointSpec("/api/all_liquidations/stats.json"),
    "all_liquidations": EndpointSpec(
        "/api/all_liquidations/{timeframe}.json", timeframe_case="lower"
    ),
    "binance_liquidations_stats": EndpointSpec(
        "/api/binance_liquidations/stats.json"
    ),
    "binance_liquidations": EndpointSpec(
        "/api/binance_liquidations/{timeframe}.json", timeframe_case="lower"
    ),
    "bybit_liquidations_stats": EndpointSpec("/api/bybit_liquidations/stats.json"),
    "bybit_liquidations": EndpointSpec(
        "/api/bybit_liquidations/{timeframe}.json", timeframe_case="lower"
    ),
    "okx_liquidations_stats": EndpointSpec("/api/okx_liquidations/stats.json"),
    "okx_liquidations": EndpointSpec(
        "/api/okx_liquidations/{timeframe}.json", timeframe_case="lower"
    ),
    "positions": EndpointSpec("/api/positions.json"),
    "positions_all": EndpointSpec("/api/positions/all.json"),
    "position_snapshots_symbol": EndpointSpec(
        "/api/position_snapshots/symbol/{symbol}", symbol_case="upper"
    ),
    "position_snapshots_stats": EndpointSpec("/api/position_snapshots/stats"),
    "whales": EndpointSpec("/api/whales.json"),
    "buyers": EndpointSpec("/api/buyers.json"),
    "depositors": EndpointSpec("/api/depositors.json"),
    "whale_addresses": EndpointSpec("/api/whale_addresses.txt"),
    "events": EndpointSpec("/api/events.json"),
    "contracts": EndpointSpec("/api/contracts.json"),
    "smart_money_rankings": EndpointSpec("/api/smart_money/rankings.json"),
    "smart_money_leaderboard": EndpointSpec("/api/smart_money/leaderboard.json"),
    "smart_money_signals": EndpointSpec(
        "/api/smart_money/signals_{duration}.json", duration_case="lower"
    ),
    "user_positions": EndpointSpec("/api/user/{address}/positions"),
    "user_fills": EndpointSpec("/api/user/{address}/fills"),
    "hlp_positions": EndpointSpec("/api/hlp/positions"),
    "hlp_trades": EndpointSpec("/api/hlp/trades"),
    "hlp_trades_stats": EndpointSpec("/api/hlp/trades/stats"),
    "hlp_positions_history": EndpointSpec("/api/hlp/positions/history"),
    "hlp_liquidators": EndpointSpec("/api/hlp/liquidators"),
    "hlp_deltas": EndpointSpec("/api/hlp/deltas"),
    "hlp_sentiment": EndpointSpec("/api/hlp/sentiment"),
    "hlp_liquidators_status": EndpointSpec("/api/hlp/liquidators/status"),
    "hlp_market_maker": EndpointSpec("/api/hlp/market-maker"),
    "hlp_timing": EndpointSpec("/api/hlp/timing"),
    "hlp_correlation": EndpointSpec("/api/hlp/correlation"),
    "hip3_candles_symbols": EndpointSpec("/api/hip3/candles/symbols"),
    "hip3_prices": EndpointSpec("/api/hip3/prices"),
    "hip3_price": EndpointSpec("/api/hip3/price/{symbol}", symbol_case="upper"),
    "hip3_candles": EndpointSpec("/api/hip3/candles/{symbol}", symbol_case="upper"),
    "hip3_ticks": EndpointSpec("/api/hip3/ticks/{symbol}", symbol_case="upper"),
    "hip3_meta": EndpointSpec("/api/hip3/meta"),
    "hip3_ticks_stats": EndpointSpec("/api/hip3_ticks/stats.json"),
    "hip3_ticks_dex": EndpointSpec(
        "/api/hip3_ticks/{dex}_{ticker}.json", ticker_case="lower", dex_case="lower"
    ),
}
