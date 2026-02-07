"""Whale insights feed (buyers/depositors/addresses)."""

from __future__ import annotations

from typing import Any, Dict, List
import logging
import time

from backend.storage import DatasetRegistry, partition_and_write
from .base import BaseFeed

logger = logging.getLogger(__name__)


class WhaleInsightsFeed(BaseFeed):
    def __init__(
        self,
        client: Any,
        *,
        registry: DatasetRegistry,
        poll_interval: float = 12.0,
        offline: bool = False,
        dataset_name: str = "whale_insights",
        timeframe: str = "live",
    ) -> None:
        super().__init__(
            name="whale_insights", poll_interval=poll_interval, offline=offline
        )
        self.client = client
        self._registry = registry
        self._dataset_name = dataset_name
        self._timeframe = timeframe

    def fetch(self) -> Dict[str, Any]:
        now_ms = int(time.time() * 1000)
        errors: List[str] = []
        payload: Dict[str, Any] = {}

        payload["buyers"] = _try_fetch(self.client, "buyers", errors)
        payload["depositors"] = _try_fetch(self.client, "depositors", errors)
        payload["whale_addresses"] = _try_fetch(self.client, "whale_addresses", errors)

        if _all_empty(payload) and errors:
            raise ConnectionError("; ".join(errors))

        payload["received_ts_ms"] = now_ms
        payload["errors"] = errors
        self._persist_snapshot(payload, now_ms)
        return payload

    def _persist_snapshot(self, payload: Dict[str, Any], timestamp_ms: int) -> None:
        try:
            record = {
                "timestamp_ms": timestamp_ms,
                "buyers": payload.get("buyers"),
                "depositors": payload.get("depositors"),
                "whale_addresses": payload.get("whale_addresses"),
            }
            partition_and_write(
                self._dataset_name,
                self._timeframe,
                timestamp_ms,
                [record],
                self._registry,
            )
        except Exception as exc:
            logger.warning(
                {"event": "whale_insights_snapshot_write_failed", "error": str(exc)}
            )


def _try_fetch(client: Any, endpoint_key: str, errors: List[str]) -> Any:
    try:
        return client.get_json(endpoint_key)
    except Exception as exc:
        errors.append(f"{endpoint_key}: {exc}")
        return None


def _all_empty(payload: Dict[str, Any]) -> bool:
    for value in payload.values():
        if value:
            return False
    return True
