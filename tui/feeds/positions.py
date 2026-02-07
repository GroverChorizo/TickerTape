"""Positions feed for MoonDev endpoints."""

from __future__ import annotations

from typing import Any, Dict, List
import logging
import time

from backend.storage import DatasetRegistry, partition_and_write
from .base import BaseFeed

logger = logging.getLogger(__name__)


class PositionsFeed(BaseFeed):
    def __init__(
        self,
        client: Any,
        *,
        registry: DatasetRegistry,
        symbol: str = "BTC",
        poll_interval: float = 12.0,
        offline: bool = False,
        dataset_name: str = "positions",
        timeframe: str = "live",
    ) -> None:
        super().__init__(name="positions", poll_interval=poll_interval, offline=offline)
        self.client = client
        self.symbol = symbol.upper()
        self._registry = registry
        self._dataset_name = dataset_name
        self._timeframe = timeframe

    def set_symbol(self, symbol: str) -> None:
        if symbol:
            self.symbol = symbol.upper()

    def fetch(self) -> Dict[str, Any]:
        now_ms = int(time.time() * 1000)
        errors: List[str] = []
        payload: Dict[str, Any] = {"symbol": self.symbol}

        payload["positions"] = _try_fetch(self.client, "positions", errors)
        payload["positions_all"] = _try_fetch(self.client, "positions_all", errors)
        payload["snapshot_symbol"] = _try_fetch(
            self.client,
            "position_snapshots_symbol",
            errors,
            symbol=self.symbol,
            params={"hours": 24},
        )
        payload["snapshot_stats"] = _try_fetch(
            self.client, "position_snapshots_stats", errors, params={"hours": 24}
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
                "symbol": payload.get("symbol"),
                "positions": payload.get("positions"),
                "positions_all": payload.get("positions_all"),
                "snapshot_symbol": payload.get("snapshot_symbol"),
                "snapshot_stats": payload.get("snapshot_stats"),
            }
            partition_and_write(
                self._dataset_name,
                self._timeframe,
                timestamp_ms,
                [record],
                self._registry,
            )
        except Exception as exc:
            logger.warning({"event": "positions_snapshot_write_failed", "error": str(exc)})


def _try_fetch(client: Any, endpoint_key: str, errors: List[str], **kwargs: Any) -> Any:
    try:
        return client.get_json(endpoint_key, **kwargs)
    except Exception as exc:
        errors.append(f"{endpoint_key}: {exc}")
        return None


def _all_empty(payload: Dict[str, Any]) -> bool:
    for key, value in payload.items():
        if key == "symbol":
            continue
        if value:
            return False
    return True
