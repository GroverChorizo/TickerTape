"""Typed models for market context data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class MarketContext:
    symbol: str
    last_price: Optional[float]
    best_bid: Optional[float]
    best_ask: Optional[float]
    spread_bps: Optional[float]
    funding_rate: Optional[float]
    open_interest: Optional[float]

    @classmethod
    def from_payload(cls, payload: Dict[str, Any], symbol: str) -> "MarketContext":
        symbol = symbol.upper()
        quick = payload.get("quick") if isinstance(payload, dict) else None
        top = _find_top_symbol(payload, symbol)
        last_price = _coerce_float((quick or {}).get("mid")) or _coerce_float(
            (quick or {}).get("best_bid")
        )
        if last_price is None and top:
            last_price = _coerce_float(top.get("last") or top.get("mid"))
        best_bid = _coerce_float((quick or {}).get("best_bid"))
        best_ask = _coerce_float((quick or {}).get("best_ask"))
        spread_bps = _coerce_float((quick or {}).get("spread"))
        funding_rate = _coerce_float(top.get("funding") if top else None)
        open_interest = _coerce_float(top.get("open_interest") if top else None)
        return cls(
            symbol=symbol,
            last_price=last_price,
            best_bid=best_bid,
            best_ask=best_ask,
            spread_bps=spread_bps,
            funding_rate=funding_rate,
            open_interest=open_interest,
        )


def _find_top_symbol(payload: Dict[str, Any], symbol: str) -> Optional[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return None
    rows = payload.get("top_coins") or []
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict) and str(row.get("symbol") or "").upper() == symbol:
            return row
    return None


def _coerce_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
