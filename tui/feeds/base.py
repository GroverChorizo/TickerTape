"""Safe feed primitives for TickerTape TUI."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import logging
import random
import time


logger = logging.getLogger(__name__)


@dataclass
class FeedResult:
    status: str
    data: Optional[Any] = None
    error: Optional[str] = None
    updated_ts_ms: Optional[int] = None
    is_lkg: bool = False


class BaseFeed:
    def __init__(
        self,
        name: str,
        poll_interval: float = 5.0,
        max_backoff: float = 30.0,
        offline: bool = False,
    ) -> None:
        self.name = name
        self.poll_interval = poll_interval
        self.max_backoff = max_backoff
        self.offline = offline
        self._backoff = 1.0
        self._stop = False
        self._last_update_ts: Optional[int] = None
        self._lkg: Optional[Any] = None
        self._latest = FeedResult(status="loading", data=None, updated_ts_ms=None)

    def stop(self) -> None:
        self._stop = True

    def latest(self) -> FeedResult:
        return self._latest

    def last_update_ts(self) -> Optional[int]:
        return self._last_update_ts

    def fetch(self) -> Any:
        raise NotImplementedError

    def fetch_result(self) -> FeedResult:
        if self.offline:
            return self._record_result(
                FeedResult(status="disconnected", data=self._lkg, error="offline mode", updated_ts_ms=self._last_update_ts),
            )
        if self._stop:
            return self._record_result(
                FeedResult(status="disconnected", data=self._lkg, error="stopped", updated_ts_ms=self._last_update_ts),
            )
        try:
            payload = self.fetch()
        except (TimeoutError, OSError) as exc:
            return self._record_result(self._error_result("disconnected", str(exc)))
        except Exception as exc:
            return self._record_result(self._error_result("error", str(exc)))
        if not payload:
            return self._record_result(
                FeedResult(
                    status="empty",
                    data=self._lkg,
                    error=None,
                    updated_ts_ms=self._last_update_ts,
                    is_lkg=self._lkg is not None,
                )
            )
        now_ms = int(time.time() * 1000)
        self._lkg = payload
        self._last_update_ts = now_ms
        self._backoff = 1.0
        return self._record_result(FeedResult(status="ok", data=payload, updated_ts_ms=now_ms))

    def next_delay(self, last_status: str) -> float:
        if last_status == "ok":
            return self.poll_interval
        jitter = random.uniform(0, 0.5)
        self._backoff = min(self._backoff * 2, self.max_backoff)
        return self._backoff + jitter

    def _error_result(self, status: str, message: str) -> FeedResult:
        if status not in {"error", "disconnected"}:
            status = "error"
        return FeedResult(
            status=status,
            data=self._lkg,
            error=message,
            updated_ts_ms=self._last_update_ts,
            is_lkg=self._lkg is not None,
        )

    def _record_result(self, result: FeedResult) -> FeedResult:
        self._latest = result
        logger.info(
            {
                "event": "feed_result",
                "feed": self.name,
                "status": result.status,
                "updated_ts_ms": result.updated_ts_ms,
                "has_lkg": result.is_lkg,
                "error": result.error,
            }
        )
        return result
