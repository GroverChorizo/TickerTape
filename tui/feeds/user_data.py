"""User data feed (wallet/account; legacy data-layer endpoints)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging
import time

from backend.storage import DatasetRegistry, partition_and_write
from .base import BaseFeed

logger = logging.getLogger(__name__)


class UserDataFeed(BaseFeed):
    def __init__(
        self,
        client: Any,
        *,
        registry: DatasetRegistry,
        address: Optional[str] = None,
        poll_interval: float = 10.0,
        offline: bool = False,
        dataset_name: str = "user_data",
        timeframe: str = "live",
    ) -> None:
        super().__init__(name="user_data", poll_interval=poll_interval, offline=offline)
        self.client = client
        self.address = address
        self._registry = registry
        self._dataset_name = dataset_name
        self._timeframe = timeframe

    def set_address(self, address: Optional[str]) -> None:
        self.address = address.strip() if isinstance(address, str) else None

    def fetch(self) -> Dict[str, Any]:
        now_ms = int(time.time() * 1000)
        address = self.address
        if not address:
            return {
                "address": None,
                "error": "No wallet address configured.",
                "received_ts_ms": now_ms,
            }

        errors: List[str] = []
        payload: Dict[str, Any] = {"address": address}
        payload["account"] = _try_fetch(self.client, "account", errors, address=address)
        payload["positions"] = _try_fetch(
            self.client, "user_positions", errors, address=address
        )
        payload["fills"] = _try_fetch(
            self.client, "user_fills", errors, address=address, params={"limit": 100}
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
                "address": payload.get("address"),
                "account": payload.get("account"),
                "positions": payload.get("positions"),
                "fills": payload.get("fills"),
            }
            partition_and_write(
                self._dataset_name,
                self._timeframe,
                timestamp_ms,
                [record],
                self._registry,
            )
        except Exception as exc:
            logger.warning({"event": "user_data_snapshot_write_failed", "error": str(exc)})


def _try_fetch(client: Any, endpoint_key: str, errors: List[str], **kwargs: Any) -> Any:
    try:
        return client.get_json(endpoint_key, **kwargs)
    except Exception as exc:
        errors.append(f"{endpoint_key}: {exc}")
        return None


def _all_empty(payload: Dict[str, Any]) -> bool:
    for key, value in payload.items():
        if key in {"address"}:
            continue
        if value:
            return False
    return True
