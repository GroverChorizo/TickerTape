"""Profile-to-endpoint feed contracts.

These mappings are derived from the authoritative Vision docs:
- ``BtheVision_v1_5_5.txt``
- ``docs/FtheVision_v1_5_5.txt``
"""

from __future__ import annotations

from typing import Dict, List


PROFILE_ENDPOINT_CONTRACTS: Dict[str, Dict[str, List[str]]] = {
    "day_trader": {
        "market_overview": ["ticks_latest", "prices", "price", "candles"],
        "orderbook": ["orderbook"],
        "whale_flow": ["whales"],
        "liquidation_stats": ["liquidations_stats", "liquidations"],
        "funding": ["binance_funding"],
        "positions": ["positions", "positions_all"],
        "smart_money": ["smart_money_rankings", "smart_money_signals"],
        "hlp": ["hlp_timing", "hlp_correlation"],
        "orderflow": ["orderflow", "orderflow_stats", "imbalance"],
    },
    "liquidation_hunter": {
        "liquidations_core": [
            "liquidations_stats",
            "liquidations",
            "all_liquidations_stats",
            "all_liquidations",
        ],
        "positions": ["positions", "positions_all", "position_snapshots_symbol"],
        "orderbook": ["orderbook"],
        "funding": ["binance_funding"],
        "whales": ["whales"],
        "hip3": ["hip3_liquidations_stats", "hip3_liquidations"],
    },
    "whale_watcher": {
        "whales": ["whales", "large_trades"],
        "whale_addresses": ["whale_addresses"],
        "depositors": ["depositors"],
        "positions": ["positions_all"],
        "smart_money": ["smart_money_rankings", "smart_money_signals"],
    },
    "funding_arbitrage": {
        "funding": ["binance_funding"],
        "hlp": ["hlp_timing", "hlp_correlation", "hlp_positions", "hlp_deltas"],
        "market_context": ["ticks_latest", "positions", "orderbook"],
    },
}
