"""Hyperliquid feed adapters for the TUI."""
from __future__ import annotations
from backend import storage, network
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import logging
import time

from .backend.storage import DatasetRegistry, partition_and_write
from .base import BaseFeed
from .url_builder import EndpointUrlBuilder
from .moondev_client import MoonDevClient

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .backend.network import NetworkClient


@dataclass
class FundingPoint:
    timestamp_ms: int
    rate: float


class HyperliquidClient:
    def __init__(
        self,
        base_url: str = "https://api.moondev.com",
        timeout: float = 10.0,
        retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self._client = MoonDevClient(base_url=self.base_url, timeout=timeout, retries=retries)

    def close(self) -> None:
        self._client.close()

    def get_json(self, endpoint_key: str, params: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
        return self._client.get_json(endpoint_key, params=params, **kwargs)

    def post_json(self, endpoint_key: str, payload: Dict[str, Any], **kwargs: Any) -> Any:
        return self._client.post_json(endpoint_key, payload, **kwargs)


class LiquidationsFeed(BaseFeed):
    def __init__(self, client: HyperliquidClient, poll_interval: float = 5.0, offline: bool = False) -> None:
        super().__init__(name="liquidations", poll_interval=poll_interval, offline=offline)
        self.client = client

    def fetch(self) -> Dict[str, Any]:
        data = self.client.get_json("liquidations_stats")
        return {"snapshot": data, "received_ts_ms": int(time.time() * 1000)}


class WhaleTradesFeed(BaseFeed):
    def __init__(self, client: HyperliquidClient, poll_interval: float = 4.0, offline: bool = False) -> None:
        super().__init__(name="whales", poll_interval=poll_interval, offline=offline)
        self.client = client

    def fetch(self) -> Dict[str, Any]:
        data = self.client.get_json("whales")
        return {"trades": data, "received_ts_ms": int(time.time() * 1000)}


class FundingRatesFeed(BaseFeed):
    def __init__(
        self,
        client: "NetworkClient",
        *,
        registry: DatasetRegistry,
        coins: Optional[List[str]] = None,
        poll_interval: float = 10.0,
        offline: bool = False,
        dataset_name: str = "funding_rates",
        timeframe: str = "live",
    ) -> None:
        super().__init__(name="funding", poll_interval=poll_interval, offline=offline)
        self.client = client
        self.coins = coins or ["BTC"]
        self._registry = registry
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
        whales = self.client.get_json("whales")
        events = _normalize_whale_events(whales)
        return {"events": events[-20:], "received_ts_ms": int(time.time() * 1000)}


def _format_http_error(method: str, url: str, response: Any) -> str:
    snippet = ""
    try:
        snippet = str(getattr(response, "text", "") or "")
    except Exception:
        snippet = ""
    snippet = snippet.replace("\r", " ").replace("\n", " ")[:200]
    return f"{method} {url} -> HTTP {response.status_code}: {snippet}"


def _format_json_error(method: str, url: str, response: Any) -> str:
    snippet = ""
    try:
        snippet = str(getattr(response, "text", "") or "")
    except Exception:
        snippet = ""
    snippet = snippet.replace("\r", " ").replace("\n", " ")[:200]
    return f"{method} {url} -> HTTP {response.status_code} (json decode error): {snippet}"


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
