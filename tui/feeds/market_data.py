"""Market data feed for the DayTrader profile."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging
import time

from backend.storage import DatasetRegistry, partition_and_write
from .base import BaseFeed, FeedResult
from .hyperliquid import HyperliquidClient

logger = logging.getLogger(__name__)


class MarketDataFeed(BaseFeed):
    def __init__(
        self,
        client: HyperliquidClient,
        *,
        registry: Optional[DatasetRegistry] = None,
        poll_interval: float = 1.5,
        offline: bool = False,
        selected_coin: str = "BTC",
        coin_cycle: Optional[List[str]] = None,
    ) -> None:
        super().__init__(
            name="market_data", poll_interval=poll_interval, offline=offline
        )
        self.client = client
        self.selected_coin = selected_coin.upper()
        self.coin_cycle = [
            c.upper() for c in (coin_cycle or ["BTC", "ETH", "SOL", "XRP", "DOGE"])
        ]
        if self.selected_coin not in self.coin_cycle:
            self.coin_cycle.insert(0, self.selected_coin)
        self._registry = registry
        self._dataset_name = "market_data"
        self._timeframe = "live"
        self._cache: Dict[str, Any] = {
            "top_coins": None,
            "quick": None,
            "orderbook": None,
            "candles_1h": None,
            "candles_1m": None,
        }
        self._last_fetch: Dict[str, float] = {
            "prices": 0.0,
            "quick": 0.0,
            "orderbook": 0.0,
            "candles": 0.0,
        }
        self._intervals = {
            "prices": 1.5,
            "quick": 1.5,
            "orderbook": 3.0,
            "candles": 15.0,
        }

    def set_selected_coin(self, symbol: str) -> None:
        symbol = symbol.strip().upper()
        if not symbol:
            return
        self.selected_coin = symbol
        if symbol not in self.coin_cycle:
            self.coin_cycle.append(symbol)

    def cycle_coin(self) -> str:
        if not self.coin_cycle:
            return self.selected_coin
        if self.selected_coin in self.coin_cycle:
            idx = self.coin_cycle.index(self.selected_coin)
            self.selected_coin = self.coin_cycle[(idx + 1) % len(self.coin_cycle)]
        else:
            self.selected_coin = self.coin_cycle[0]
        return self.selected_coin

    def fetch(self) -> Dict[str, Any]:
        now = time.monotonic()
        errors: List[str] = []
        disconnect_flags: List[bool] = []
        updated_any = False

        if self._due(now, "prices"):
            try:
                raw = self.client.get_json("ticks_latest")
                parsed = _parse_top_coins(raw)
                if parsed:
                    self._cache["top_coins"] = parsed
                    updated_any = True
            except Exception as exc:
                errors.append(f"prices: {exc}")
                disconnect_flags.append(isinstance(exc, (TimeoutError, OSError)))
                logger.warning(
                    {"event": "market_data_prices_failed", "error": str(exc)}
                )
                try:
                    raw = self.client.get_json("prices")
                    parsed = _parse_top_coins(raw)
                    if parsed:
                        self._cache["top_coins"] = parsed
                        updated_any = True
                except Exception as exc2:
                    errors.append(f"prices_fallback: {exc2}")
                    disconnect_flags.append(isinstance(exc2, (TimeoutError, OSError)))
                    logger.warning(
                        {
                            "event": "market_data_prices_fallback_failed",
                            "error": str(exc2),
                        }
                    )
            self._last_fetch["prices"] = now

        if self._due(now, "quick"):
            try:
                raw = self.client.get_json("price", symbol=self.selected_coin)
                parsed = _parse_quick_price(raw, self.selected_coin)
                if parsed:
                    self._cache["quick"] = parsed
                    updated_any = True
            except Exception as exc:
                errors.append(f"quick: {exc}")
                disconnect_flags.append(isinstance(exc, (TimeoutError, OSError)))
                logger.warning({"event": "market_data_quick_failed", "error": str(exc)})
            self._last_fetch["quick"] = now

        if self._due(now, "orderbook"):
            try:
                raw = self.client.get_json("orderbook", symbol=self.selected_coin)
                parsed = _parse_orderbook(raw, depth=10)
                if parsed:
                    self._cache["orderbook"] = parsed
                    updated_any = True
            except Exception as exc:
                errors.append(f"orderbook: {exc}")
                disconnect_flags.append(isinstance(exc, (TimeoutError, OSError)))
                logger.warning(
                    {"event": "market_data_orderbook_failed", "error": str(exc)}
                )
            self._last_fetch["orderbook"] = now

        if self._due(now, "candles"):
            try:
                candles_1h = self.client.get_json(
                    "candles",
                    symbol=self.selected_coin,
                    params={"interval": "1h", "limit": 10},
                )
                parsed_1h = _parse_candles(candles_1h)
                if parsed_1h:
                    self._cache["candles_1h"] = parsed_1h[-10:]
                    updated_any = True
            except Exception as exc:
                errors.append(f"candles_1h: {exc}")
                disconnect_flags.append(isinstance(exc, (TimeoutError, OSError)))
                logger.warning(
                    {
                        "event": "market_data_candles_failed",
                        "error": str(exc),
                        "interval": "1h",
                    }
                )

            try:
                candles_1m = self.client.get_json(
                    "candles",
                    symbol=self.selected_coin,
                    params={"interval": "1m", "limit": 10},
                )
                parsed_1m = _parse_candles(candles_1m)
                if parsed_1m:
                    self._cache["candles_1m"] = parsed_1m[-10:]
                    updated_any = True
            except Exception as exc:
                errors.append(f"candles_1m: {exc}")
                disconnect_flags.append(isinstance(exc, (TimeoutError, OSError)))
                logger.warning(
                    {
                        "event": "market_data_candles_failed",
                        "error": str(exc),
                        "interval": "1m",
                    }
                )
            self._last_fetch["candles"] = now

        if errors and not updated_any:
            if disconnect_flags and all(disconnect_flags):
                raise ConnectionError("; ".join(errors))
            raise RuntimeError("; ".join(errors))

        payload = {
            "ts_ms": int(time.time() * 1000),
            "selected_coin": self.selected_coin,
            "top_coins": self._cache.get("top_coins"),
            "quick": self._cache.get("quick"),
            "orderbook": self._cache.get("orderbook"),
            "candles_1h": self._cache.get("candles_1h"),
            "candles_1m": self._cache.get("candles_1m"),
            "errors": errors,
        }
        if not self._has_any_data(payload):
            return {}
        self._persist_snapshot(payload)
        return payload

    def push(self, payload: Any) -> FeedResult:
        """Merge pushed payloads into the cached market snapshot.

        Streaming endpoints may deliver partial payloads (prices, orderbook,
        ticks). We normalize and merge those into the cache, then emit a
        full MarketData payload for panels to render.
        """
        updated = False
        if isinstance(payload, dict):
            # Full payloads can be pushed directly.
            if isinstance(payload.get("top_coins"), list):
                self._cache["top_coins"] = payload.get("top_coins")
                updated = True
            if isinstance(payload.get("quick"), dict):
                self._cache["quick"] = payload.get("quick")
                updated = True
            if isinstance(payload.get("orderbook"), dict):
                self._cache["orderbook"] = payload.get("orderbook")
                updated = True
            if isinstance(payload.get("candles_1h"), list):
                self._cache["candles_1h"] = payload.get("candles_1h")
                updated = True
            if isinstance(payload.get("candles_1m"), list):
                self._cache["candles_1m"] = payload.get("candles_1m")
                updated = True

            # Try to parse known shapes (prices, orderbook, ticks)
            top = _parse_top_coins(payload)
            if top:
                self._cache["top_coins"] = top
                updated = True
            orderbook = _parse_orderbook(payload, depth=10)
            if orderbook:
                self._cache["orderbook"] = orderbook
                updated = True

            symbol = _coerce_str(
                payload.get("symbol")
                or payload.get("coin")
                or (payload.get("tick") or {}).get("symbol")
            )
            if symbol and symbol.upper() == self.selected_coin:
                quick = _parse_quick_price(payload, self.selected_coin)
                if quick:
                    self._cache["quick"] = quick
                    updated = True

        if not updated:
            return self.latest()
        payload_out = {
            "ts_ms": int(time.time() * 1000),
            "selected_coin": self.selected_coin,
            "top_coins": self._cache.get("top_coins"),
            "quick": self._cache.get("quick"),
            "orderbook": self._cache.get("orderbook"),
            "candles_1h": self._cache.get("candles_1h"),
            "candles_1m": self._cache.get("candles_1m"),
            "errors": [],
        }
        return super().push(payload_out)

    def _due(self, now: float, key: str) -> bool:
        return (now - self._last_fetch[key]) >= self._intervals[key]

    def _has_any_data(self, payload: Dict[str, Any]) -> bool:
        return any(
            payload.get(key)
            for key in ["top_coins", "quick", "orderbook", "candles_1h", "candles_1m"]
        )

    def _persist_snapshot(self, payload: Dict[str, Any]) -> None:
        if not self._registry:
            return
        try:
            ts_ms = payload.get("ts_ms") or int(time.time() * 1000)
            record = {
                "timestamp_ms": ts_ms,
                "selected_coin": payload.get("selected_coin"),
                "top_coins": payload.get("top_coins"),
                "quick": payload.get("quick"),
                "orderbook": payload.get("orderbook"),
                "candles_1h": payload.get("candles_1h"),
                "candles_1m": payload.get("candles_1m"),
            }
            partition_and_write(
                self._dataset_name,
                self._timeframe,
                ts_ms,
                [record],
                self._registry,
            )
        except Exception as exc:
            logger.warning(
                {"event": "market_data_snapshot_write_failed", "error": str(exc)}
            )


def _parse_top_coins(raw: Any) -> List[Dict[str, Any]]:
    items = raw
    if isinstance(raw, dict):
        items = (
            raw.get("data")
            or raw.get("prices")
            or raw.get("coins")
            or raw.get("ticks")
            or raw.get("latest")
            or raw.get("result")
            or raw.get("snapshot")
        )
    if isinstance(items, dict):
        funding_map = raw.get("funding_rates") if isinstance(raw, dict) else None
        oi_map = raw.get("open_interest") if isinstance(raw, dict) else None
        ts = (
            _coerce_int(
                raw.get("timestamp_ms") or raw.get("timestamp") or raw.get("time")
            )
            if isinstance(raw, dict)
            else None
        )
        parsed: List[Dict[str, Any]] = []
        for symbol, price in items.items():
            entry = price if isinstance(price, dict) else {}
            parsed.append(
                {
                    "symbol": _coerce_str(symbol) or "?",
                    "last": _coerce_float(
                        entry.get("price")
                        or entry.get("latest_price")
                        or entry.get("latestPrice")
                        or price
                    ),
                    "mid": _coerce_float(
                        entry.get("mid") or entry.get("mid_price") or entry.get("midPrice")
                    ),
                    "funding": _coerce_float(
                        (funding_map.get(symbol) if isinstance(funding_map, dict) else None)
                        or entry.get("funding")
                        or entry.get("funding_rate")
                        or entry.get("fundingRate")
                        or entry.get("fundingRateHourly")
                    ),
                    "open_interest": _coerce_float(
                        (oi_map.get(symbol) if isinstance(oi_map, dict) else None)
                        or entry.get("open_interest")
                        or entry.get("openInterest")
                        or entry.get("openInterestUsd")
                    ),
                    "timestamp_ms": _coerce_int(
                        entry.get("timestamp_ms")
                        or entry.get("timestamp")
                        or entry.get("time")
                        or ts
                    ),
                }
            )
        return parsed
    if not isinstance(items, list):
        return []
    parsed: List[Dict[str, Any]] = []
    for entry in items:
        if not isinstance(entry, dict):
            continue
        symbol = _coerce_str(
            entry.get("symbol")
            or entry.get("coin")
            or entry.get("asset")
            or entry.get("ticker")
        )
        if not symbol:
            continue
        parsed.append(
            {
                "symbol": symbol,
                "last": _coerce_float(
                    entry.get("last")
                    or entry.get("price")
                    or entry.get("latest_price")
                    or entry.get("latestPrice")
                    or entry.get("mark")
                    or entry.get("mid")
                ),
                "mid": _coerce_float(
                    entry.get("mid") or entry.get("mid_price") or entry.get("midPrice")
                ),
                "funding": _coerce_float(
                    entry.get("funding")
                    or entry.get("funding_rate")
                    or entry.get("fundingRate")
                    or entry.get("fundingRateHourly")
                ),
                "open_interest": _coerce_float(
                    entry.get("open_interest")
                    or entry.get("openInterest")
                    or entry.get("oi")
                    or entry.get("openInterestUsd")
                ),
                "timestamp_ms": _coerce_int(
                    entry.get("timestamp_ms")
                    or entry.get("timestamp")
                    or entry.get("time")
                    or entry.get("ts")
                ),
            }
        )
    return parsed


def _parse_quick_price(raw: Any, symbol: str) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    payload = {
        "symbol": symbol,
        "best_bid": _coerce_float(
            raw.get("best_bid") or raw.get("bestBid") or raw.get("bid")
        ),
        "best_ask": _coerce_float(
            raw.get("best_ask") or raw.get("bestAsk") or raw.get("ask")
        ),
        "mid": _coerce_float(
            raw.get("mid") or raw.get("mid_price") or raw.get("midPrice")
        ),
        "spread": _coerce_float(
            raw.get("spread") or raw.get("spread_bps") or raw.get("spreadBps")
        ),
        "timestamp_ms": _coerce_int(
            raw.get("timestamp_ms") or raw.get("timestamp") or raw.get("time")
        ),
    }
    if not any(
        payload.get(key) is not None
        for key in ["best_bid", "best_ask", "mid", "spread"]
    ):
        return None
    return payload


def _parse_orderbook(raw: Any, depth: int = 10) -> Optional[Dict[str, Any]]:
    bids = asks = ts = None
    if isinstance(raw, dict):
        levels = raw.get("levels")
        if isinstance(levels, dict):
            bids = raw.get("bids") or raw.get("bid") or levels.get("bids")
            asks = raw.get("asks") or raw.get("ask") or levels.get("asks")
        elif isinstance(levels, list) and len(levels) >= 2:
            bids = raw.get("bids") or raw.get("bid") or levels[0]
            asks = raw.get("asks") or raw.get("ask") or levels[1]
        else:
            bids = raw.get("bids") or raw.get("bid")
            asks = raw.get("asks") or raw.get("ask")
        ts = raw.get("timestamp_ms") or raw.get("timestamp") or raw.get("time")
    elif isinstance(raw, list):
        if len(raw) >= 2 and isinstance(raw[0], list) and isinstance(raw[1], list):
            bids, asks = raw[0], raw[1]
        else:
            bids = raw
            asks = []
    bid_levels = _parse_book_side(bids, depth)
    ask_levels = _parse_book_side(asks, depth)
    if not bid_levels and not ask_levels:
        return None
    return {
        "bids": bid_levels,
        "asks": ask_levels,
        "timestamp_ms": _coerce_int(ts),
    }


def _parse_book_side(raw: Any, depth: int) -> List[Dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    levels: List[Dict[str, Any]] = []
    for entry in raw[:depth]:
        price: Optional[float] = None
        size: Optional[float] = None
        if isinstance(entry, dict):
            price = _coerce_float(
                entry.get("price") or entry.get("px") or entry.get("p")
            )
            size = _coerce_float(
                entry.get("size") or entry.get("qty") or entry.get("s")
            )
        elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
            price = _coerce_float(entry[0])
            size = _coerce_float(entry[1])
        if price is None and size is None:
            continue
        levels.append({"price": price, "size": size})
    return levels


def _parse_candles(raw: Any) -> List[Dict[str, Any]]:
    if isinstance(raw, dict):
        raw = raw.get("candles") or raw.get("data") or raw.get("snapshot")
    if not isinstance(raw, list):
        return []
    candles: List[Dict[str, Any]] = []
    for entry in raw:
        candle = _parse_candle_entry(entry)
        if candle:
            candles.append(candle)
    return candles


def _parse_candle_entry(entry: Any) -> Optional[Dict[str, Any]]:
    if isinstance(entry, dict):
        ts = _coerce_int(
            entry.get("t")
            or entry.get("time")
            or entry.get("timestamp")
            or entry.get("ts")
        )
        if ts is None:
            return None
        return {
            "timestamp_ms": ts,
            "open": _coerce_float(entry.get("o") or entry.get("open")),
            "high": _coerce_float(entry.get("h") or entry.get("high")),
            "low": _coerce_float(entry.get("l") or entry.get("low")),
            "close": _coerce_float(entry.get("c") or entry.get("close")),
            "volume": _coerce_float(entry.get("v") or entry.get("volume")),
            "trades": _coerce_int(entry.get("n") or entry.get("trades")),
        }
    if isinstance(entry, (list, tuple)) and len(entry) >= 5:
        ts = _coerce_int(entry[0])
        if ts is None:
            return None
        return {
            "timestamp_ms": ts,
            "open": _coerce_float(entry[1]),
            "high": _coerce_float(entry[2]),
            "low": _coerce_float(entry[3]),
            "close": _coerce_float(entry[4]),
            "volume": _coerce_float(entry[5]) if len(entry) > 5 else None,
            "trades": _coerce_int(entry[6]) if len(entry) > 6 else None,
        }
    return None


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
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
