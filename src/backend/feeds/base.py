"""Base feed definitions for TickerTape."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional
import time


@dataclass
class FeedState:
    status: str
    last_update_ts_ms: Optional[int]
    error: Optional[str] = None


class BaseFeed:
    def __init__(
        self, name: str, poll_interval: float = 5.0, offline: bool = False
    ) -> None:
        self.name = name
        self.poll_interval = poll_interval
        self.offline = offline
        self.state = FeedState(
            status="offline" if offline else "idle", last_update_ts_ms=None
        )
        self._callback: Optional[Callable[[dict], None]] = None
        self._latest: Optional[dict] = None

    def subscribe(self, callback: Callable[[dict], None]) -> None:
        self._callback = callback

    def latest(self) -> Optional[dict]:
        return self._latest

    def set_error(self, error: str) -> None:
        self.state = FeedState(
            status="error", last_update_ts_ms=self.state.last_update_ts_ms, error=error
        )

    def set_ok(self) -> None:
        self.state = FeedState(
            status="ok", last_update_ts_ms=int(time.time() * 1000), error=None
        )

    def update(self, payload: dict) -> None:
        self._latest = payload
        self.set_ok()
        if self._callback:
            self._callback(payload)

    def fetch(self) -> dict:
        raise NotImplementedError
