"""Live stream manager for TickerTape."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Callable, Any
import time
import asyncio

from tui.providers.hyperliquid import HyperliquidProvider, HyperliquidStreamer


class StreamStatus(str, Enum):
    LIVE = "live"
    DEGRADED = "degraded"
    OFFLINE = "offline"


@dataclass(frozen=True)
class StreamHealth:
    last_seen_ms: Optional[int]
    status: StreamStatus


class LiveStreamManager:
    """Lifecycle manager for Hyperliquid streaming in the TUI."""

    def __init__(
        self,
        provider: HyperliquidProvider,
        *,
        stale_after_s: float = 8.0,
        dead_after_s: float = 20.0,
        streamer_factory: Optional[Callable[[HyperliquidProvider], Any]] = None,
    ) -> None:
        self._provider = provider
        self._stale_after_ms = int(stale_after_s * 1000)
        self._dead_after_ms = int(dead_after_s * 1000)
        self._streamer_factory = streamer_factory or (lambda p: HyperliquidStreamer(p))
        self._streamer: Optional[HyperliquidStreamer] = None
        self._active = False
        self._last_error: Optional[str] = None

    @property
    def active(self) -> bool:
        return self._active and self._streamer is not None

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        try:
            self._streamer = self._streamer_factory(self._provider)
            # tuned for fast UI updates without flooding
            self._streamer.start(poll_interval=1.0, market_agg_ms=250, market_max_hz=6)
        except Exception as exc:
            self._last_error = str(exc)
            self._streamer = None
            self._active = False

    def stop(self) -> None:
        if not self._streamer:
            self._active = False
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            loop.create_task(self._streamer.stop())
        else:
            asyncio.run(self._streamer.stop())
        self._streamer = None
        self._active = False

    def stream_last_seen(self) -> Dict[str, Optional[int]]:
        return {name: feed.last_update_ts() for name, feed in self._feeds().items()}

    def health(self) -> Dict[str, StreamHealth]:
        now_ms = int(time.time() * 1000)
        health: Dict[str, StreamHealth] = {}
        for name, feed in self._feeds().items():
            last = feed.last_update_ts()
            if not last:
                status = StreamStatus.OFFLINE
            else:
                age = now_ms - int(last)
                if age >= self._dead_after_ms:
                    status = StreamStatus.OFFLINE
                elif age >= self._stale_after_ms:
                    status = StreamStatus.DEGRADED
                else:
                    status = StreamStatus.LIVE
            health[name] = StreamHealth(last_seen_ms=last, status=status)
        return health

    def summary(self) -> str:
        health = self.health()
        total = len(health)
        live = sum(1 for item in health.values() if item.status == StreamStatus.LIVE)
        if total == 0:
            return "WS: 0/0 OFFLINE"
        if live == 0:
            overall = "OFFLINE"
        elif live == total:
            overall = "LIVE"
        else:
            overall = "DEGRADED"
        return f"WS: {live}/{total} {overall}"

    def _feeds(self) -> Dict[str, Any]:
        feeds = {}
        for name, attr in (
            ("market", "_market_feed"),
            ("liquidations", "_liquidations_feed"),
            ("whales", "_whales_feed"),
            ("funding", "_funding_feed"),
            ("events", "_events_feed"),
        ):
            feed = getattr(self._provider, attr, None)
            if feed is not None:
                feeds[name] = feed
        return feeds
