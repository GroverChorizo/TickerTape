"""Hyperliquid feed adapters for the TUI."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import logging
import random
import time

from backend.storage import DatasetRegistry, partition_and_write
from .base import BaseFeed

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from backend.network import NetworkClient


@dataclass
class FundingPoint:
    timestamp_ms: int
    rate: float


class HyperliquidClient:
    def __init__(
        self,
        base_url: str = "https://api.hyperliquid.xyz",
        timeout: float = 10.0,
        retries: int = 3,
    ) -> None:
        import httpx

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self._httpx = httpx
        self._client = httpx.Client(timeout=httpx.Timeout(timeout))

    def close(self) -> None:
        self._client.close()

    def get_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request("GET", path, params=params)

    def post_json(self, path: str, payload: Dict[str, Any]) -> Any:
        return self._request("POST", path, json=payload)

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}{path}"
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                resp = self._client.request(method, url, **kwargs)
                logger.info(
                    {
                        "event": "http_request",
                        "method": method,
                        "path": path,
                        "status": resp.status_code,
                        "attempt": attempt,
                    }
                )
                if resp.status_code == 429 or 500 <= resp.status_code < 600:
                    last_exc = RuntimeError(f"HTTP {resp.status_code}")
                    time.sleep(self._backoff(attempt))
                    continue
                if 400 <= resp.status_code < 500:
                    raise self._httpx.HTTPStatusError(f"HTTP {resp.status_code}", request=None, response=None)
                return resp.json()
            except self._httpx.RequestError as exc:
                last_exc = exc
                logger.warning({"event": "http_error", "path": path, "attempt": attempt, "error": str(exc)})
                time.sleep(self._backoff(attempt))
        raise ConnectionError(f"Failed to fetch {path}: {last_exc}")

    @staticmethod
    def _backoff(attempt: int) -> float:
        return 0.5 * (2 ** (attempt - 1)) + random.uniform(0, 0.25)


class LiquidationsFeed(BaseFeed):
    def __init__(self, client: HyperliquidClient, poll_interval: float = 5.0, offline: bool = False) -> None:
        super().__init__(name="liquidations", poll_interval=poll_interval, offline=offline)
        self.client = client

    def fetch(self) -> Dict[str, Any]:
        data = self.client.get_json("/api/liquidations/stats.json")
        return {"snapshot": data, "received_ts_ms": int(time.time() * 1000)}


class WhaleTradesFeed(BaseFeed):
    def __init__(self, client: HyperliquidClient, poll_interval: float = 4.0, offline: bool = False) -> None:
        super().__init__(name="whales", poll_interval=poll_interval, offline=offline)
        self.client = client

    def fetch(self) -> Dict[str, Any]:
        data = self.client.get_json("/api/whales.json")
        return {"trades": data, "received_ts_ms": int(time.time() * 1000)}


class FundingRatesFeed(BaseFeed):
    def __init__(
        self,
        client: "NetworkClient",
        coins: Optional[List[str]] = None,
        poll_interval: float = 20.0,
        offline: bool = False,
        registry: Optional[DatasetRegistry] = None,
        dataset_name: str = "funding_rates",
        timeframe: str = "live",
    ) -> None:
        super().__init__(name="funding", poll_interval=poll_interval, offline=offline)
        self.client = client
        self.coins = coins or ["BTC"]
        self._registry = registry or DatasetRegistry()
        self._dataset_name = dataset_name
        self._timeframe = timeframe

    def fetch(self) -> Dict[str, Any]:
        end_ms = int(time.time() * 1000)
        start_ms = end_ms - 60 * 60 * 1000
        payloads: Dict[str, Dict[str, Any]] = {}
        for coin in self.coins:
            history = self.client.post(
                "info",
                {"type": "fundingHistory", "coin": coin, "startTime": start_ms},
            )
            points = _parse_funding_history(history)
            latest = points[-1] if points else None
            payloads[coin] = {
                "history": [p.__dict__ for p in points[-12:]],
                "latest": latest.__dict__ if latest else None,
            }
        payload = {"funding": payloads, "received_ts_ms": end_ms}
        self._persist_snapshot(payload, end_ms)
        return payload

    def _persist_snapshot(self, payload: Dict[str, Any], timestamp_ms: int) -> None:
        try:
            record = {
                "timestamp_ms": timestamp_ms,
                "funding": payload.get("funding", {}),
            }
            partition_and_write(
                self._dataset_name,
                self._timeframe,
                timestamp_ms,
                [record],
                self._registry,
            )
        except Exception as exc:
            logger.warning({"event": "funding_snapshot_write_failed", "error": str(exc)})


class EventStreamFeed(BaseFeed):
    def __init__(self, client: HyperliquidClient, poll_interval: float = 4.0, offline: bool = False) -> None:
        super().__init__(name="event_stream", poll_interval=poll_interval, offline=offline)
        self.client = client

    def fetch(self) -> Dict[str, Any]:
        whales = self.client.get_json("/api/whales.json")
        events = _normalize_whale_events(whales)
        return {"events": events[-20:], "received_ts_ms": int(time.time() * 1000)}


def _parse_funding_history(raw: Any) -> List[FundingPoint]:
    points: List[FundingPoint] = []
    if not isinstance(raw, list):
        return points
    for item in raw:
        if not isinstance(item, dict):
            continue
        ts = item.get("time") or item.get("timestamp") or item.get("timestamp_ms")
        rate = item.get("fundingRate")
        try:
            ts_ms = int(ts)
            rate_f = float(rate)
        except (TypeError, ValueError):
            continue
        points.append(FundingPoint(timestamp_ms=ts_ms, rate=rate_f))
    return points


def _normalize_whale_events(raw: Any) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    if isinstance(raw, dict):
        raw = raw.get("trades") or raw.get("data") or raw.get("events")
    if not isinstance(raw, list):
        return events
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        event = {
            "timestamp_ms": entry.get("timestamp_ms") or entry.get("timestamp") or entry.get("time"),
            "symbol": entry.get("symbol") or entry.get("coin"),
            "side": entry.get("side") or entry.get("direction"),
            "size": entry.get("size") or entry.get("amount") or entry.get("qty"),
            "price": entry.get("price"),
            "wallet": entry.get("wallet") or entry.get("wallet_address") or entry.get("address"),
            "raw": entry,
        }
        events.append(event)
    return events
