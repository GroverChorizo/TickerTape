"""Base provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable, Optional


class Provider(ABC):
    """Abstract provider interface for market data feeds."""

    @abstractmethod
    def get_ticks(self, symbol: str) -> Iterable[Any]:
        raise NotImplementedError

    @abstractmethod
    def get_orderbook(self, symbol: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def get_liquidations(self) -> Iterable[Any]:
        raise NotImplementedError

    @abstractmethod
    def get_whale_trades(self) -> Iterable[Any]:
        raise NotImplementedError

    @abstractmethod
    def get_funding_rates(self) -> Iterable[Any]:
        raise NotImplementedError

    @abstractmethod
    def get_positions(self) -> Iterable[Any]:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    def diagnostics(self) -> Optional[dict[str, Any]]:
        return None
