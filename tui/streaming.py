"""Streaming helpers for TickerTape.

This module exposes two layers:
1. ``LiveStreamManager`` for provider-level WS lifecycle and health summaries.
2. ``StreamSupervisor`` compatibility shim for feed-level polling used in tests
   and legacy call sites.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Callable, Any
import time
import asyncio

from tui.providers.hyperliquid import HyperliquidProvider, HyperliquidStreamer
from tui.feeds.base import FeedStatus


class StreamStatus(str, Enum):
    LIVE = "live"
    DEGRADED = "degraded"
    OFFLINE = "offline"


@dataclass(frozen=True)
class StreamHealth:
    last_seen_ms: Optional[int]
    status: StreamStatus


@dataclass(frozen=True)
class StreamMetric:
    active: bool
    lag_ms: Optional[int]
    reconnect_count: int
    error_count: int
    messages_received: int
    last_error: Optional[str] = None


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
        reconnects = sum(metric.reconnect_count for metric in self.metrics().values())
        return f"WS: {live}/{total} {overall} R:{reconnects}"

    def metrics(self) -> Dict[str, StreamMetric]:
        """Structured per-stream metrics, including lag and reconnect counts."""
        now_ms = int(time.time() * 1000)
        if self._streamer and hasattr(self._streamer, "stats"):
            try:
                raw = self._streamer.stats()
            except Exception:
                raw = {}
            metrics: Dict[str, StreamMetric] = {}
            if isinstance(raw, dict):
                for name, payload in raw.items():
                    if not isinstance(payload, dict):
                        continue
                    lag = payload.get("lag_ms")
                    if lag is None:
                        last_msg = payload.get("last_message_ts_ms")
                        if last_msg is not None:
                            try:
                                lag = max(0, now_ms - int(last_msg))
                            except Exception:
                                lag = None
                    metrics[str(name)] = StreamMetric(
                        active=bool(payload.get("connected") and payload.get("running")),
                        lag_ms=int(lag) if lag is not None else None,
                        reconnect_count=int(payload.get("reconnect_count") or 0),
                        error_count=int(payload.get("error_count") or 0),
                        messages_received=int(payload.get("messages_received") or 0),
                        last_error=(
                            str(payload.get("last_error"))
                            if payload.get("last_error") is not None
                            else None
                        ),
                    )
            if metrics:
                return metrics

        # Fallback metrics derived from feed freshness when streamer stats
        # are unavailable.
        fallback: Dict[str, StreamMetric] = {}
        for name, item in self.health().items():
            lag_ms = None
            if item.last_seen_ms is not None:
                lag_ms = max(0, now_ms - int(item.last_seen_ms))
            fallback[name] = StreamMetric(
                active=item.status == StreamStatus.LIVE,
                lag_ms=lag_ms,
                reconnect_count=0,
                error_count=0,
                messages_received=0,
                last_error=None,
            )
        return fallback

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


class StreamSupervisor:
    """Compatibility feed supervisor used by tests and simple polling flows.

    The supervisor supports both:
    - ``src.backend.feeds.base.BaseFeed`` style feeds (`fetch`, `update`, `set_error`)
    - ``tui.feeds.base.BaseFeed`` style feeds (`fetch_result`, `latest`)
    """

    def __init__(self) -> None:
        self._feeds: Dict[str, Any] = {}

    def register(self, feed: Any) -> None:
        name = getattr(feed, "name", None)
        if not name:
            raise ValueError("feed must define a name")
        self._feeds[str(name)] = feed

    async def run_once(self, name: str) -> Any:
        if name not in self._feeds:
            raise KeyError(f"unknown feed: {name}")
        feed = self._feeds[name]

        # Newer TUI feeds expose a typed fetch_result contract.
        if hasattr(feed, "fetch_result"):
            try:
                return feed.fetch_result()
            except Exception as exc:
                self._set_tui_error(feed, str(exc))
                return None

        # Legacy backend feeds expose fetch/update + mutable state.
        try:
            payload = feed.fetch()
        except Exception as exc:
            if hasattr(feed, "set_error"):
                feed.set_error(str(exc))
            return None

        if hasattr(feed, "update"):
            feed.update(payload)
        return payload

    def _set_tui_error(self, feed: Any, message: str) -> None:
        # Use internal error helpers when available so latest() reflects error state.
        if hasattr(feed, "_error_result") and hasattr(feed, "_record_result"):
            try:
                result = feed._error_result(FeedStatus.ERROR, message)
                feed._record_result(result)
                return
            except Exception:
                pass
        # Fallback for legacy-style feeds.
        if hasattr(feed, "set_error"):
            feed.set_error(message)
