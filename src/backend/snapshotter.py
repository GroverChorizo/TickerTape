"""Snapshot scheduler and runner.

Provides a small scheduler to run snapshot emission on configured cadences, and a `run_once` helper for CLI/tools.
"""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional
import logging

from .liquidations_feed import LiquidationsFeed, DEFAULT_CADENCE_SECONDS
from .storage import DatasetRegistry, partition_and_write

logger = logging.getLogger(__name__)


class SnapshotScheduler:
    def __init__(self, feed: LiquidationsFeed, registry: DatasetRegistry, cadences: Optional[Dict[str, int]] = None) -> None:
        self.feed = feed
        self.registry = registry
        self.cadences = cadences or DEFAULT_CADENCE_SECONDS
        self._tasks: Dict[str, asyncio.Task] = {}
        self._running = False

    async def _worker(self, timeframe: str, interval_seconds: int) -> None:
        logger.info({"event": "snapshot_worker_start", "timeframe": timeframe, "interval": interval_seconds})
        while self._running:
            now = datetime.now(timezone.utc)
            # align window to cadence: floor to multiple
            epoch = int(now.timestamp())
            window_start = epoch - (epoch % interval_seconds)
            window_end = window_start + interval_seconds
            window_start_ms = window_start * 1000
            window_end_ms = window_end * 1000
            provenance = {"run_id": f"snapshot_{timeframe}_{window_start_ms}"}
            snapshot = self.feed.compute_snapshot(timeframe, window_start_ms, window_end_ms, provenance=provenance)
            # write to parquet and register
            path = partition_and_write("liquidations_snapshots", timeframe, window_start_ms, [snapshot], self.registry)
            logger.info({"event": "snapshot_emitted", "timeframe": timeframe, "path": str(path)})
            await asyncio.sleep(interval_seconds)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        loop = asyncio.get_event_loop()
        for tf, interval in self.cadences.items():
            self._tasks[tf] = loop.create_task(self._worker(tf, interval))

    def stop(self) -> None:
        self._running = False
        for t in self._tasks.values():
            t.cancel()
        self._tasks = {}


def run_once(feed: LiquidationsFeed, registry: DatasetRegistry, timeframe: str, window_start_ts_ms: Optional[int] = None) -> str:
    """Run a single snapshot emission for the given timeframe.

    If window_start_ts_ms is None, align to current UTC timeframe.
    Returns the path to the written file as string.
    """
    interval = DEFAULT_CADENCE_SECONDS.get(timeframe)
    if interval is None:
        raise ValueError("Unknown timeframe")
    now = datetime.now(timezone.utc)
    epoch = int(now.timestamp())
    if window_start_ts_ms is None:
        window_start = epoch - (epoch % interval)
    else:
        window_start = int(window_start_ts_ms // 1000)
    window_end = window_start + interval
    window_start_ms = window_start * 1000
    provenance = {"run_id": f"snapshot_{timeframe}_{window_start_ms}"}
    snapshot = feed.compute_snapshot(timeframe, window_start_ms, window_end * 1000, provenance=provenance)
    path = partition_and_write("liquidations_snapshots", timeframe, window_start_ms, [snapshot], registry)
    return str(path)
