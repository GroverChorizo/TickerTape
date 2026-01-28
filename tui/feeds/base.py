"""Safe feed primitives for TickerTape TUI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Union
import logging
import random
import time
from enum import Enum

class FeedStatus(str, Enum):
    LOADING = "loading"
    OK = "ok"
    EMPTY = "empty"
    ERROR = "error"
    DISCONNECTED = "disconnected"


def _as_status(status: Union[FeedStatus, str]) -> FeedStatus:
    if isinstance(status, FeedStatus):
        return status
    try:
        return FeedStatus(status)
    except Exception:
        return FeedStatus.ERROR

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeedResult:
    status: Union[FeedStatus, str]
    data: Optional[Any] = None
    error: Optional[str] = None
    updated_ts_ms: Optional[int] = None
    is_lkg: bool = False

    def __post_init__(self) -> None:
        # Coerce string statuses to FeedStatus for backwards compatibility.
        if isinstance(self.status, str):
            try:
                object.__setattr__(self, "status", FeedStatus(self.status))
            except ValueError:
                object.__setattr__(self, "status", FeedStatus.ERROR)


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
        # Return an immutable copy to protect internal state.
        return FeedResult(**vars(self._latest))

    def last_update_ts(self) -> Optional[int]:
        return self._last_update_ts

    def fetch(self) -> Any:
        """
        Fetch fresh data.

        Must return:
          - None if no new data is available
          - A payload object if successful

        Must raise:
          - TimeoutError / OSError for transient failures
          - Other Exceptions for fatal errors
        """
        raise NotImplementedError

    def fetch_result(self) -> FeedResult:
        if self.offline:
            return self._record_result(
                self._error_result(FeedStatus.DISCONNECTED, "offline mode")
            )
        if self._stop:
            return self._record_result(
                self._error_result(FeedStatus.DISCONNECTED, "stopped")
            )
        try:
            payload = self.fetch()
        except (TimeoutError, OSError) as exc:
            return self._record_result(self._error_result(FeedStatus.DISCONNECTED, str(exc)))
        except Exception as exc:
            return self._record_result(self._error_result(FeedStatus.ERROR, str(exc)))
        # Explicit contract: None means no new data
        if payload is None:
            return self._record_result(
                FeedResult(
                    status=FeedStatus.EMPTY,
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
        return self._record_result(
            FeedResult(status=FeedStatus.OK, data=payload, updated_ts_ms=now_ms)
        )

    def next_delay(self, last_status: Union[FeedStatus, str]) -> float:
        # Accept legacy string statuses too
        status = last_status
        if isinstance(last_status, str):
            try:
                status = FeedStatus(last_status)
            except ValueError:
                status = FeedStatus.ERROR
        if status == FeedStatus.OK:
            return self.poll_interval
        jitter = random.uniform(0, 0.5)
        self._backoff = min(self._backoff * 2, self.max_backoff)
        return self._backoff + jitter

    def _error_result(self, status: Union[FeedStatus, str], message: str) -> FeedResult:
        if isinstance(status, str):
            try:
                status = FeedStatus(status)
            except ValueError:
                status = FeedStatus.ERROR
        if status not in {FeedStatus.ERROR, FeedStatus.DISCONNECTED}:
            status = FeedStatus.ERROR
        return FeedResult(
            status=status,
            data=self._lkg,
            error=message,
            updated_ts_ms=self._last_update_ts,
            is_lkg=self._lkg is not None,
        )

    def _record_result(self, result: FeedResult) -> FeedResult:
        # Keep the last result and log at appropriate level.
        self._latest = result
        payload = {
            "event": "feed_result",
            "feed": self.name,
            "status": result.status.value if isinstance(result.status, FeedStatus) else result.status,
            "updated_ts_ms": result.updated_ts_ms,
            "has_lkg": result.is_lkg,
            "error": result.error,
        }
        if result.status == FeedStatus.OK:
            logger.debug(payload)
        else:
            logger.warning(payload)
        return result

    def push(self, payload: Any) -> FeedResult:
        """Accept a pushed payload (e.g., from a stream) and record it as OK.

        This method is safe to call from streaming supervisors and will update
        internal last-known-good data and timestamps.
        """
        now_ms = int(time.time() * 1000)
        self._lkg = payload
        self._last_update_ts = now_ms
        self._backoff = 1.0
        return self._record_result(
            FeedResult(status=FeedStatus.OK, data=payload, updated_ts_ms=now_ms)
        )
