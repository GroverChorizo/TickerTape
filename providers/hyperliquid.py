"""Hyperliquid provider implementation (HTTP + optional streaming)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Dict, Optional
import asyncio
import time

from backend.network import NetworkClient
from tui.feeds.liquidations import _normalize_event
from tui.feeds.moondev_client import MoonDevClient

from .base import Provider
from .models import (
    FundingRate,
    LiquidationEvent,
    OrderBookLevel,
    OrderBookSnapshot,
    Position,
    Tick,
    WhaleTrade,
)


@dataclass
class CacheEntry:
    ts: float
    payload: list[LiquidationEvent]


class DirectHyperliquidClient:
    """Direct HTTP client wrapper using backend.network.NetworkClient."""

    def __init__(
        self,
        client: Optional[NetworkClient] = None,
        *,
        fallback: Optional[MoonDevClient] = None,
    ) -> None:
        self._client = client or NetworkClient()
        self._fallback = fallback

    def get_json(self, endpoint_key: str, params: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
        params = params or {}
        if endpoint_key == "info":
            payload = params or kwargs or {}
            return self._client.post("info", payload)
        if endpoint_key == "orderbook":
            symbol = params.get("symbol") or kwargs.get("symbol")
            return self._client.post("info", {"type": "l2Book", "coin": symbol})
        if endpoint_key in {"price", "prices"}:
            data = self._client.post("info", {"type": "allMids"})
            symbol = params.get("symbol") or kwargs.get("symbol")
            if endpoint_key == "price" and symbol and isinstance(data, dict):
                price = data.get(symbol.upper()) or data.get(symbol.lower())
                return {"symbol": symbol, "price": price}
            return data
        if endpoint_key == "ticks":
            symbol = params.get("symbol") or kwargs.get("symbol")
            return self._client.post("info", {"type": "recentTrades", "coin": symbol})
        try:
            return self._client.get(endpoint_key, params=params)
        except Exception:
            if self._fallback:
                return self._fallback.get_json(endpoint_key, params=params, **kwargs)
            raise

    def close(self) -> None:
        if hasattr(self._client, "_client"):
            try:
                self._client._client.close()  # type: ignore[attr-defined]
            except Exception:
                pass


class HyperliquidProvider(Provider):
    """Provider backed by direct Hyperliquid HTTP with MoonDev fallback."""

    def __init__(
        self,
        *,
        client: Optional[Any] = None,
        direct_client: Optional[DirectHyperliquidClient] = None,
        moondev_client: Optional[MoonDevClient] = None,
        cache_ttl_s: float = 5.0,
        now_fn: Optional[Callable[[], float]] = None,
        use_moondev: bool = False,
    ) -> None:
        if client is not None:
            self._client = client
        elif use_moondev:
            self._client = moondev_client or MoonDevClient()
        else:
            self._client = direct_client or DirectHyperliquidClient(
                fallback=moondev_client
            )
        self._cache_ttl_s = cache_ttl_s
        self._now = now_fn or time.monotonic
        self._liquidations_cache: Optional[CacheEntry] = None

    def get_liquidations(self) -> list[LiquidationEvent]:
        now = self._now()
        cache = self._liquidations_cache
        if cache and (now - cache.ts) <= self._cache_ttl_s:
            return cache.payload
        raw = self._client.get_json("liquidations_stats")
        events = _extract_events(raw)
        self._liquidations_cache = CacheEntry(ts=now, payload=events)
        return events

    def get_ticks(self, symbol: str) -> list[Tick]:
        raw = self._client.get_json("price", symbol=symbol)
        if isinstance(raw, dict) and "price" not in raw:
            price = raw.get(symbol.upper()) or raw.get(symbol.lower())
            raw = {"symbol": symbol, "price": price}
        payloads = raw if isinstance(raw, list) else [raw]
        ticks: list[Tick] = []
        for entry in payloads:
            if not isinstance(entry, dict):
                continue
            ticks.append(
                Tick(
                    ts_ms=int(entry.get("timestamp_ms") or entry.get("ts_ms") or time.time() * 1000),
                    symbol=str(entry.get("symbol") or symbol).upper(),
                    price=float(entry.get("price") or entry.get("last") or entry.get("px") or 0.0),
                    size=_coerce_float(entry.get("size")),
                    exchange=str(entry.get("exchange") or "hyperliquid"),
                )
            )
        return ticks

    def get_orderbook(self, symbol: str) -> OrderBookSnapshot:
        raw = self._client.get_json("orderbook", symbol=symbol)
        return _parse_orderbook(raw, symbol)

    def get_whale_trades(self) -> list[WhaleTrade]:
        raw = self._client.get_json("whales")
        entries = _ensure_list(raw)
        trades: list[WhaleTrade] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            trades.append(
                WhaleTrade(
                    ts_ms=int(entry.get("timestamp_ms") or entry.get("ts_ms") or time.time() * 1000),
                    symbol=str(entry.get("symbol") or entry.get("coin") or "?").upper(),
                    side=str(entry.get("side") or entry.get("direction") or "unknown"),
                    notional_usd=_coerce_float(
                        entry.get("notional_usd") or entry.get("value_usd") or entry.get("notional")
                    ),
                    price=_coerce_float(entry.get("price") or entry.get("px")),
                    size=_coerce_float(entry.get("size") or entry.get("amount") or entry.get("qty")),
                    exchange=str(entry.get("exchange") or "hyperliquid"),
                    wallet=_coerce_str(entry.get("wallet") or entry.get("wallet_address") or entry.get("address")),
                )
            )
        return trades

    def get_funding_rates(self) -> list[FundingRate]:
        raw = self._client.get_json("funding")
        entries = _ensure_list(raw)
        rates: list[FundingRate] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            rates.append(
                FundingRate(
                    ts_ms=int(entry.get("timestamp_ms") or entry.get("time") or time.time() * 1000),
                    symbol=str(entry.get("symbol") or entry.get("coin") or "?").upper(),
                    rate=float(entry.get("fundingRate") or entry.get("rate") or 0.0),
                    interval_hours=_coerce_float(entry.get("interval_hours") or entry.get("interval")),
                    exchange=str(entry.get("exchange") or "hyperliquid"),
                    annualized_pct=_coerce_float(entry.get("annualized_pct")),
                )
            )
        return rates

    def get_positions(self) -> list[Position]:
        raw = self._client.get_json("positions")
        entries = _ensure_list(raw)
        positions: list[Position] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            positions.append(
                Position(
                    ts_ms=int(entry.get("timestamp_ms") or entry.get("ts_ms") or time.time() * 1000),
                    symbol=str(entry.get("symbol") or entry.get("coin") or "?").upper(),
                    side=str(entry.get("side") or entry.get("direction") or "unknown"),
                    size=float(entry.get("size") or entry.get("position_size") or 0.0),
                    entry_price=_coerce_float(entry.get("entry_price") or entry.get("entryPrice")),
                    liquidation_price=_coerce_float(entry.get("liquidation_price") or entry.get("liquidationPrice")),
                    exchange=str(entry.get("exchange") or "hyperliquid"),
                )
            )
        return positions

    def close(self) -> None:
        try:
            if hasattr(self._client, "close"):
                self._client.close()
        except Exception:
            pass

    async def stream_liquidations(self) -> AsyncIterator[LiquidationEvent]:
        async for message in self._stream_endpoint("liquidations_stats"):
            for event in _extract_events(message):
                yield event

    async def stream_whale_trades(self) -> AsyncIterator[WhaleTrade]:
        async for message in self._stream_endpoint("whales"):
            for trade in self.get_whale_trades_from_payload(message):
                yield trade

    async def stream_orderbook(self, symbol: str) -> AsyncIterator[OrderBookSnapshot]:
        async for message in self._stream_endpoint("orderbook", params={"symbol": symbol}):
            yield _parse_orderbook(message, symbol)

    async def stream_ticks(self, symbol: str) -> AsyncIterator[Tick]:
        async for message in self._stream_endpoint("price", params={"symbol": symbol}):
            payloads = message if isinstance(message, list) else [message]
            for entry in payloads:
                if not isinstance(entry, dict):
                    continue
                yield Tick(
                    ts_ms=int(entry.get("timestamp_ms") or entry.get("ts_ms") or time.time() * 1000),
                    symbol=str(entry.get("symbol") or symbol).upper(),
                    price=float(entry.get("price") or entry.get("last") or entry.get("px") or 0.0),
                    size=_coerce_float(entry.get("size")),
                    exchange=str(entry.get("exchange") or "hyperliquid"),
                )

    async def stream_funding_rates(self) -> AsyncIterator[FundingRate]:
        async for message in self._stream_endpoint("funding"):
            for entry in _ensure_list(message):
                if not isinstance(entry, dict):
                    continue
                yield FundingRate(
                    ts_ms=int(entry.get("timestamp_ms") or entry.get("time") or time.time() * 1000),
                    symbol=str(entry.get("symbol") or entry.get("coin") or "?").upper(),
                    rate=float(entry.get("fundingRate") or entry.get("rate") or 0.0),
                    interval_hours=_coerce_float(entry.get("interval_hours") or entry.get("interval")),
                    exchange=str(entry.get("exchange") or "hyperliquid"),
                    annualized_pct=_coerce_float(entry.get("annualized_pct")),
                )

    async def stream_positions(self) -> AsyncIterator[Position]:
        async for message in self._stream_endpoint("positions"):
            for entry in _ensure_list(message):
                if not isinstance(entry, dict):
                    continue
                yield Position(
                    ts_ms=int(entry.get("timestamp_ms") or entry.get("ts_ms") or time.time() * 1000),
                    symbol=str(entry.get("symbol") or entry.get("coin") or "?").upper(),
                    side=str(entry.get("side") or entry.get("direction") or "unknown"),
                    size=float(entry.get("size") or entry.get("position_size") or 0.0),
                    entry_price=_coerce_float(entry.get("entry_price") or entry.get("entryPrice")),
                    liquidation_price=_coerce_float(entry.get("liquidation_price") or entry.get("liquidationPrice")),
                    exchange=str(entry.get("exchange") or "hyperliquid"),
                )

    def get_whale_trades_from_payload(self, raw: Any) -> list[WhaleTrade]:
        entries = _ensure_list(raw)
        trades: list[WhaleTrade] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            trades.append(
                WhaleTrade(
                    ts_ms=int(entry.get("timestamp_ms") or entry.get("ts_ms") or time.time() * 1000),
                    symbol=str(entry.get("symbol") or entry.get("coin") or "?").upper(),
                    side=str(entry.get("side") or entry.get("direction") or "unknown"),
                    notional_usd=_coerce_float(
                        entry.get("notional_usd") or entry.get("value_usd") or entry.get("notional")
                    ),
                    price=_coerce_float(entry.get("price") or entry.get("px")),
                    size=_coerce_float(entry.get("size") or entry.get("amount") or entry.get("qty")),
                    exchange=str(entry.get("exchange") or "hyperliquid"),
                    wallet=_coerce_str(entry.get("wallet") or entry.get("wallet_address") or entry.get("address")),
                )
            )
        return trades

    async def _stream_endpoint(
        self, endpoint_key: str, *, params: Optional[Dict[str, Any]] = None, poll_interval: float = 2.0
    ) -> AsyncIterator[Any]:
        params = params or {}
        ws_factory = getattr(self._client, "ws_connect", None)
        if callable(ws_factory):
            cm = await ws_factory(endpoint_key, **params)
            async with cm as ws_iter:
                async for message in ws_iter:
                    yield message
            return
        while True:
            payload = await asyncio.to_thread(self._client.get_json, endpoint_key, **params)
            yield payload
            await asyncio.sleep(poll_interval)


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
        normalized = _normalize_event(entry, source="hyperliquid")
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


def _parse_orderbook(raw: Any, symbol: str) -> OrderBookSnapshot:
    bids: list[OrderBookLevel] = []
    asks: list[OrderBookLevel] = []
    if isinstance(raw, dict):
        raw_bids = raw.get("bids") or raw.get("bid") or raw.get("levels", [[], []])[0]
        raw_asks = raw.get("asks") or raw.get("ask") or raw.get("levels", [[], []])[1]
        bids = _parse_levels(raw_bids)
        asks = _parse_levels(raw_asks)
        ts = int(raw.get("timestamp_ms") or raw.get("ts_ms") or time.time() * 1000)
        sym = str(raw.get("symbol") or raw.get("coin") or symbol).upper()
    else:
        ts = int(time.time() * 1000)
        sym = symbol.upper()
    return OrderBookSnapshot(ts_ms=ts, symbol=sym, bids=bids, asks=asks, exchange="hyperliquid")


def _parse_levels(raw: Any) -> list[OrderBookLevel]:
    levels: list[OrderBookLevel] = []
    if not isinstance(raw, list):
        return levels
    for entry in raw:
        if isinstance(entry, dict):
            price = entry.get("price") or entry.get("px")
            size = entry.get("size") or entry.get("sz")
        elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
            price, size = entry[0], entry[1]
        else:
            continue
        try:
            levels.append(OrderBookLevel(price=float(price), size=float(size)))
        except (TypeError, ValueError):
            continue
    return levels


def _ensure_list(raw: Any) -> list[Any]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("data", "rows", "events", "trades", "items"):
            value = raw.get(key)
            if isinstance(value, list):
                return value
        return []
    return []


def _coerce_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        text = str(value).strip()
    except Exception:
        return None
    return text or None
