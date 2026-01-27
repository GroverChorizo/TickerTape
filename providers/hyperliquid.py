"""Hyperliquid provider implementation (HTTP snapshot)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional
import time

from tui.feeds.liquidations import _normalize_event
from tui.feeds.moondev_client import MoonDevClient

from .base import Provider
from .models import (
    FundingRate,
    LiquidationEvent,
    OrderBookSnapshot,
    Position,
    Tick,
    WhaleTrade,
)


@dataclass
class CacheEntry:
    ts: float
    payload: list[LiquidationEvent]


class HyperliquidProvider(Provider):
    """Provider backed by MoonDev HTTP endpoints with retry/backoff."""

    def __init__(
        self,
        *,
        client: Optional[MoonDevClient] = None,
        base_url: str = "https://api.moondev.com",
        cache_ttl_s: float = 5.0,
        now_fn: Optional[Callable[[], float]] = None,
    ) -> None:
        self._client = client or MoonDevClient(base_url=base_url)
        self._cache_ttl_s = cache_ttl_s
        self._now = now_fn or time.monotonic
        self._liquidations_cache: Optional[CacheEntry] = None

    def get_liquidations(self) -> list[LiquidationEvent]:
        now = self._now()
        cache = self._liquidations_cache
        if cache and (now - cache.ts) <= self._cache_ttl_s:
            return cache.payload
        raw = self._client.get_json("liquidations", timeframe="1h")
        events = _extract_events(raw)
        self._liquidations_cache = CacheEntry(ts=now, payload=events)
        return events

    def get_ticks(self, symbol: str) -> list[Tick]:
        raise NotImplementedError("Tick data provider not implemented yet.")

    def get_orderbook(self, symbol: str) -> OrderBookSnapshot:
        raise NotImplementedError("Orderbook provider not implemented yet.")

    def get_whale_trades(self) -> list[WhaleTrade]:
        raise NotImplementedError("Whale trades provider not implemented yet.")

    def get_funding_rates(self) -> list[FundingRate]:
        raise NotImplementedError("Funding rates provider not implemented yet.")

    def get_positions(self) -> list[Position]:
        raise NotImplementedError("Positions provider not implemented yet.")

    def close(self) -> None:
        self._client.close()


def _extract_events(raw: Any) -> list[LiquidationEvent]:
    events: list[LiquidationEvent] = []
    if isinstance(raw, dict):
        raw_events = (
            raw.get("liquidations")
            or raw.get("events")
            or raw.get("data")
            or raw.get("rows")
        )
    else:
        raw_events = raw
    if not isinstance(raw_events, list):
        return events
    for entry in raw_events:
        if not isinstance(entry, dict):
            continue
        normalized = _normalize_event(entry, source="moondev")
        if normalized is None:
            continue
        events.append(
            LiquidationEvent(
                ts_ms=normalized.ts_ms,
                symbol=normalized.symbol,
                side=normalized.side,
                notional_usd=normalized.notional_usd,
                price=normalized.price,
                size=normalized.size,
                exchange=normalized.source,
                liquidated_wallet=normalized.liquidated_wallet,
            )
        )
    return events
