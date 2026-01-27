"""Typed data models for provider interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Tick:
    ts_ms: int
    symbol: str
    price: float
    size: Optional[float] = None
    exchange: Optional[str] = None


@dataclass(frozen=True)
class OrderBookLevel:
    price: float
    size: float


@dataclass(frozen=True)
class OrderBookSnapshot:
    ts_ms: int
    symbol: str
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    exchange: Optional[str] = None


@dataclass(frozen=True)
class LiquidationEvent:
    ts_ms: int
    symbol: str
    side: str
    notional_usd: Optional[float]
    price: Optional[float] = None
    size: Optional[float] = None
    exchange: Optional[str] = None
    liquidated_wallet: Optional[str] = None


@dataclass(frozen=True)
class WhaleTrade:
    ts_ms: int
    symbol: str
    side: str
    notional_usd: Optional[float]
    price: Optional[float] = None
    size: Optional[float] = None
    exchange: Optional[str] = None
    wallet: Optional[str] = None


@dataclass(frozen=True)
class FundingRate:
    ts_ms: int
    symbol: str
    rate: float
    interval_hours: Optional[float] = None
    exchange: Optional[str] = None
    annualized_pct: Optional[float] = None


@dataclass(frozen=True)
class Position:
    ts_ms: int
    symbol: str
    side: str
    size: float
    entry_price: Optional[float] = None
    liquidation_price: Optional[float] = None
    exchange: Optional[str] = None
