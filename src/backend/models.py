"""Canonical, deterministic data models for Hyperliquid data streams.

- Use dataclasses for immutability and simple serialization
- Enforce runtime validation in __post_init__
- Keep meta deterministic and JSON-serializable (Optional[Dict[str, str]])
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, List, Literal


from datetime import timezone


def _iso(dt: datetime) -> str:
    # Ensure timezone-aware UTC ISO 8601 string
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware UTC")
    return dt.astimezone(timezone.utc).isoformat()

@dataclass(frozen=True)
class TradeEvent:
    timestamp: datetime
    symbol: str
    side: Literal["buy", "sell"]
    price: float
    size: float
    trade_id: str
    meta: Optional[Dict[str, str]] = field(default=None)

    def __post_init__(self) -> None:
        # Ensure timezone-aware UTC timestamp
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("TradeEvent.timestamp must be timezone-aware UTC")
        if self.price <= 0:
            raise ValueError("TradeEvent.price must be positive")
        if self.size <= 0:
            raise ValueError("TradeEvent.size must be positive")
        if self.meta is not None:
            for k, v in self.meta.items():
                if not isinstance(k, str) or not isinstance(v, str):
                    raise TypeError("TradeEvent.meta must be Dict[str, str]")

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["timestamp"] = _iso(self.timestamp)
        return d


@dataclass(frozen=True)
class LiquidationEvent:
    timestamp: datetime
    symbol: str
    side: Literal["long", "short"]
    price: float
    size: float
    liq_id: str
    meta: Optional[Dict[str, str]] = field(default=None)

    def __post_init__(self) -> None:
        # Ensure timezone-aware UTC timestamp
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("LiquidationEvent.timestamp must be timezone-aware UTC")
        if self.price <= 0:
            raise ValueError("LiquidationEvent.price must be positive")
        if self.size <= 0:
            raise ValueError("LiquidationEvent.size must be positive")
        if self.meta is not None:
            for k, v in self.meta.items():
                if not isinstance(k, str) or not isinstance(v, str):
                    raise TypeError("LiquidationEvent.meta must be Dict[str, str]")
    def to_dict(self) -> Dict:
        d = asdict(self)
        d["timestamp"] = _iso(self.timestamp)
        return d


@dataclass(frozen=True)
class FundingEvent:
    timestamp: datetime
    symbol: str
    rate: float  # hourly rate in fractional form, e.g., 0.00012 == 0.012%
    period: str  # e.g., '1h'
    meta: Optional[Dict[str, str]] = field(default=None)

    def __post_init__(self) -> None:
        # Ensure timezone-aware UTC timestamp
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("FundingEvent.timestamp must be timezone-aware UTC")
        if not isinstance(self.rate, (float, int)):
            raise TypeError("FundingEvent.rate must be numeric")
        if self.meta is not None:
            for k, v in self.meta.items():
                if not isinstance(k, str) or not isinstance(v, str):
                    raise TypeError("FundingEvent.meta must be Dict[str, str]")
    def to_dict(self) -> Dict:
        d = asdict(self)
        d["timestamp"] = _iso(self.timestamp)
        return d


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    meta: Optional[Dict[str, str]] = field(default=None)

    def __post_init__(self) -> None:
        # Ensure timezone-aware UTC timestamp
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("Candle.timestamp must be timezone-aware UTC")
        if not (self.high >= max(self.open, self.close, self.low)):
            raise ValueError("Candle.high must be >= open, close, low")
        if not (self.low <= min(self.open, self.close, self.high)):
            raise ValueError("Candle.low must be <= open, close, high")
        if self.volume < 0:
            raise ValueError("Candle.volume must be >= 0")
        if self.meta is not None:
            for k, v in self.meta.items():
                if not isinstance(k, str) or not isinstance(v, str):
                    raise TypeError("Candle.meta must be Dict[str, str]")
    def to_dict(self) -> Dict:
        d = asdict(self)
        d["timestamp"] = _iso(self.timestamp)
        return d


# Optional: L2Snapshot (implementation-defined, JSON-serializable)
@dataclass(frozen=True)
class L2Snapshot:
    timestamp: datetime
    symbol: str
    bids: List[List[float]]  # [[price, size], ...]
    asks: List[List[float]]
    meta: Optional[Dict[str, str]] = field(default=None)

    def __post_init__(self) -> None:
        if any(p <= 0 or s <= 0 for level in self.bids for p, s in [level]):
            raise ValueError("L2Snapshot bids must have positive price and size")
        if any(p <= 0 or s <= 0 for level in self.asks for p, s in [level]):
            raise ValueError("L2Snapshot asks must have positive price and size")
        if self.meta is not None:
            for k, v in self.meta.items():
                if not isinstance(k, str) or not isinstance(v, str):
                    raise TypeError("L2Snapshot.meta must be Dict[str, str]")

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["timestamp"] = _iso(self.timestamp)
        return d