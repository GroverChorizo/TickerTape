"""Stream supervisor for backend feeds."""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, Optional

from backend.feeds.base import BaseFeed
from tui.feeds.base import BaseFeed as TuiFeedBase, FeedStatus, _as_status

logger = logging.getLogger(__name__)


class StreamSupervisor:
    def __init__(self) -> None:
        self._tasks: Dict[str, asyncio.Task] = {}
        self._feeds: Dict[str, BaseFeed] = {}
        self._running = False

    def register(self, feed: BaseFeed | TuiFeedBase) -> None:
        self._feeds[feed.name] = feed

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        for feed in self._feeds.values():
            self._tasks[feed.name] = asyncio.create_task(self._poll(feed))

    def stop(self) -> None:
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        self._tasks = {}

    async def _poll(self, feed: BaseFeed | TuiFeedBase) -> None:
        backoff = 1.0
        while self._running:
            try:
                if isinstance(feed, TuiFeedBase):
                    result = feed.fetch_result()
                    status = _as_status(result.status)
                    backoff = 1.0 if status == FeedStatus.OK else backoff
                    delay = feed.next_delay(result.status)
                else:
                    payload = feed.fetch()
                    feed.update(payload)
                    backoff = 1.0
                    delay = (
                        feed.poll_interval if feed.state.status != "error" else backoff
                    )
            except Exception as exc:
                logger.warning(
                    {"event": "feed_error", "feed": feed.name, "error": str(exc)}
                )
                if isinstance(feed, TuiFeedBase):
                    feed.fetch_result()
                    backoff = min(backoff * 2, feed.max_backoff)
                    delay = backoff
                else:
                    feed.set_error(str(exc))
                    backoff = min(backoff * 2, 30.0)
                    delay = backoff
            await asyncio.sleep(delay)

    async def run_once(self, feed_name: str) -> None:
        feed = self._feeds[feed_name]
        try:
            if isinstance(feed, TuiFeedBase):
                feed.fetch_result()
            else:
                payload = feed.fetch()
                feed.update(payload)
        except Exception as exc:
            if isinstance(feed, TuiFeedBase):
                feed.fetch_result()
            else:
                feed.set_error(str(exc))
            logger.warning(
                {"event": "feed_error", "feed": feed.name, "error": str(exc)}
            )
