"""Stub implementations for Vision-referenced feeds: Orderbook L2, FundingRates, Whale feed.

These are minimal, with schemas and empty polling loops. They register datasets in the DatasetRegistry when instantiated.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, List
from datetime import datetime, timezone
import asyncio
import logging

from .storage import DatasetRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OrderbookL2Snapshot:
    timestamp: datetime
    symbol: str
    bids: List[List[float]]
    asks: List[List[float]]
    meta: Optional[Dict[str, str]] = None


@dataclass(frozen=True)
class FundingRate:
    timestamp: datetime
    symbol: str
    rate: float
    period: str
    meta: Optional[Dict[str, str]] = None


@dataclass(frozen=True)
class WhaleTrade:
    timestamp: datetime
    symbol: str
    side: str
    size: float
    price: float
    meta: Optional[Dict[str, str]] = None


class BaseFeedStub:
    def __init__(self, registry: DatasetRegistry, dataset_name: str) -> None:
        self.registry = registry
        self.dataset_name = dataset_name
        # Register an empty dataset entry so frontend sees it
        self.registry.register_partition(self.dataset_name, "_placeholder")

    async def start_polling(self) -> None:
        # Empty polling loop - TODO: implement source-specific poller
        logger.info({"event": "start_polling_stub", "dataset": self.dataset_name})
        while True:
            await asyncio.sleep(60)


class OrderbookFeed(BaseFeedStub):
    def __init__(self, registry: DatasetRegistry) -> None:
        super().__init__(registry, "feed=orderbook_l2")


class FundingRatesFeed(BaseFeedStub):
    def __init__(self, registry: DatasetRegistry) -> None:
        super().__init__(registry, "feed=funding_rates")


class WhaleFeed(BaseFeedStub):
    def __init__(self, registry: DatasetRegistry) -> None:
        super().__init__(registry, "feed=whale_trades")
