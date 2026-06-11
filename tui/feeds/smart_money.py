"""Smart money feed (legacy data-layer endpoints)."""

from __future__ import annotations

from typing import Any, Dict, List
import logging
import time

from backend.storage import DatasetRegistry, partition_and_write
from .base import BaseFeed

logger = logging.getLogger(__name__)


class SmartMoneyFeed(BaseFeed):
    def __init__(
        self,
        client: Any,
        *,
        registry: DatasetRegistry,
        poll_interval: float = 8.0,
        offline: bool = False,
        dataset_name: str = "smart_money",
        timeframe: str = "live",
    ) -> None:
        super().__init__(name="smart_money", poll_interval=poll_interval, offline=offline)
        self.client = client
        self._registry = registry
        self._dataset_name = dataset_name
        self._timeframe = timeframe

    def fetch(self) -> Dict[str, Any]:
        now_ms = int(time.time() * 1000)
        errors: List[str] = []
        payload: Dict[str, Any] = {}

        payload["rankings"] = _try_fetch(self.client, "smart_money_rankings", errors)
        payload["leaderboard"] = _try_fetch(
            self.client, "smart_money_leaderboard", errors
        )
        payload["signals_10m"] = _try_fetch(
            self.client, "smart_money_signals", errors, duration="10m"
        )
        payload["signals_1h"] = _try_fetch(
            self.client, "smart_money_signals", errors, duration="1h"
        )
        payload["signals_24h"] = _try_fetch(
            self.client, "smart_money_signals", errors, duration="24h"
        )

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
                "rankings": payload.get("rankings"),
                "leaderboard": payload.get("leaderboard"),
                "signals_10m": payload.get("signals_10m"),
                "signals_1h": payload.get("signals_1h"),
                "signals_24h": payload.get("signals_24h"),
            }
            partition_and_write(
                self._dataset_name,
                self._timeframe,
                timestamp_ms,
                [record],
                self._registry,
            )
        except Exception as exc:
            logger.warning({"event": "smart_money_snapshot_write_failed", "error": str(exc)})


def _try_fetch(client: Any, endpoint_key: str, errors: List[str], **kwargs: Any) -> Any:
    try:
        return client.get_json(endpoint_key, **kwargs)
    except Exception as exc:
        errors.append(f"{endpoint_key}: {exc}")
        return None


def _all_empty(payload: Dict[str, Any]) -> bool:
    for value in payload.values():
        if value:
            return False
    return True
