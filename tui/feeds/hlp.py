"""Hyperliquidity Provider (HLP) feed (legacy data-layer endpoints)."""

from __future__ import annotations

from typing import Any, Dict, List
import logging
import time

from backend.storage import DatasetRegistry, partition_and_write
from .base import BaseFeed

logger = logging.getLogger(__name__)


class HlpFeed(BaseFeed):
    def __init__(
        self,
        client: Any,
        *,
        registry: DatasetRegistry,
        poll_interval: float = 12.0,
        offline: bool = False,
        dataset_name: str = "hlp",
        timeframe: str = "live",
    ) -> None:
        super().__init__(name="hlp", poll_interval=poll_interval, offline=offline)
        self.client = client
        self._registry = registry
        self._dataset_name = dataset_name
        self._timeframe = timeframe

    def fetch(self) -> Dict[str, Any]:
        now_ms = int(time.time() * 1000)
        errors: List[str] = []
        payload: Dict[str, Any] = {}

        payload["positions"] = _try_fetch(self.client, "hlp_positions", errors)
        payload["trades"] = _try_fetch(self.client, "hlp_trades", errors)
        payload["trades_stats"] = _try_fetch(self.client, "hlp_trades_stats", errors)
        payload["positions_history"] = _try_fetch(
            self.client, "hlp_positions_history", errors, params={"hours": 24}
        )
        payload["liquidators"] = _try_fetch(self.client, "hlp_liquidators", errors)
        payload["deltas"] = _try_fetch(
            self.client, "hlp_deltas", errors, params={"hours": 24}
        )
        payload["sentiment"] = _try_fetch(self.client, "hlp_sentiment", errors)
        payload["liquidators_status"] = _try_fetch(
            self.client, "hlp_liquidators_status", errors
        )
        payload["market_maker"] = _try_fetch(
            self.client, "hlp_market_maker", errors
        )
        payload["timing"] = _try_fetch(self.client, "hlp_timing", errors)
        payload["correlation"] = _try_fetch(
            self.client, "hlp_correlation", errors
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
                "positions": payload.get("positions"),
                "trades": payload.get("trades"),
                "trades_stats": payload.get("trades_stats"),
                "positions_history": payload.get("positions_history"),
                "liquidators": payload.get("liquidators"),
                "deltas": payload.get("deltas"),
                "sentiment": payload.get("sentiment"),
                "liquidators_status": payload.get("liquidators_status"),
                "market_maker": payload.get("market_maker"),
                "timing": payload.get("timing"),
                "correlation": payload.get("correlation"),
            }
            partition_and_write(
                self._dataset_name,
                self._timeframe,
                timestamp_ms,
                [record],
                self._registry,
            )
        except Exception as exc:
            logger.warning({"event": "hlp_snapshot_write_failed", "error": str(exc)})


def _try_fetch(
    client: Any, endpoint_key: str, errors: List[str], **kwargs: Any
) -> Any:
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
