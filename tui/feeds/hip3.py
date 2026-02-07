"""HIP-3 feed for MoonDev endpoints."""

from __future__ import annotations

from typing import Any, Dict, List
import logging
import time

from backend.storage import DatasetRegistry, partition_and_write
from .base import BaseFeed

logger = logging.getLogger(__name__)


class Hip3Feed(BaseFeed):
    def __init__(
        self,
        client: Any,
        *,
        registry: DatasetRegistry,
        poll_interval: float = 12.0,
        offline: bool = False,
        dataset_name: str = "hip3",
        timeframe: str = "live",
    ) -> None:
        super().__init__(name="hip3", poll_interval=poll_interval, offline=offline)
        self.client = client
        self._registry = registry
        self._dataset_name = dataset_name
        self._timeframe = timeframe

    def fetch(self) -> Dict[str, Any]:
        now_ms = int(time.time() * 1000)
        errors: List[str] = []
        payload: Dict[str, Any] = {}

        payload["prices"] = _try_fetch(self.client, "hip3_prices", errors)
        payload["symbols"] = _try_fetch(self.client, "hip3_candles_symbols", errors)
        payload["meta"] = _try_fetch(self.client, "hip3_meta", errors)
        payload["price_btc"] = _try_fetch(
            self.client, "hip3_price", errors, symbol="BTC"
        )
        payload["ticks_btc"] = _try_fetch(
            self.client, "hip3_ticks", errors, symbol="BTC"
        )
        payload["ticks_stats"] = _try_fetch(self.client, "hip3_ticks_stats", errors)
        payload["ticks_hl_btc"] = _try_fetch(
            self.client, "hip3_ticks_dex", errors, dex="hl", ticker="btc"
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
                "prices": payload.get("prices"),
                "symbols": payload.get("symbols"),
                "meta": payload.get("meta"),
                "price_btc": payload.get("price_btc"),
                "ticks_btc": payload.get("ticks_btc"),
                "ticks_stats": payload.get("ticks_stats"),
                "ticks_hl_btc": payload.get("ticks_hl_btc"),
            }
            partition_and_write(
                self._dataset_name,
                self._timeframe,
                timestamp_ms,
                [record],
                self._registry,
            )
        except Exception as exc:
            logger.warning({"event": "hip3_snapshot_write_failed", "error": str(exc)})


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
