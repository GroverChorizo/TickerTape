"""Base provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Optional

from .models import (
    FundingRate,
    LiquidationEvent,
    OrderBookSnapshot,
    Position,
    Tick,
    WhaleTrade,
)


class Provider(ABC):
    """Abstract provider interface for market data feeds."""

    @abstractmethod
    def get_ticks(self, symbol: str) -> list[Tick]:
        raise NotImplementedError

    @abstractmethod
    def get_orderbook(self, symbol: str) -> OrderBookSnapshot:
        raise NotImplementedError

    @abstractmethod
    def get_liquidations(self) -> list[LiquidationEvent]:
        raise NotImplementedError

    @abstractmethod
    def get_whale_trades(self) -> list[WhaleTrade]:
        raise NotImplementedError

    @abstractmethod
    def get_funding_rates(self) -> list[FundingRate]:
        raise NotImplementedError

    @abstractmethod
    def get_positions(self) -> list[Position]:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    def diagnostics(self) -> Optional[dict[str, Any]]:
        return None

    async def stream_ticks(self, symbol: str) -> AsyncIterator[Tick]:
        raise NotImplementedError

    async def stream_orderbook(self, symbol: str) -> AsyncIterator[OrderBookSnapshot]:
        raise NotImplementedError

    async def stream_liquidations(self) -> AsyncIterator[LiquidationEvent]:
        raise NotImplementedError

    async def stream_whale_trades(self) -> AsyncIterator[WhaleTrade]:
        raise NotImplementedError

    async def stream_funding_rates(self) -> AsyncIterator[FundingRate]:
        raise NotImplementedError

    async def stream_positions(self) -> AsyncIterator[Position]:
        raise NotImplementedError
