"""Minimal async WebSocket supervisor with reconnect/backoff.

This module provides a small, dependency-free supervisor that accepts an
`async_connect` context factory (async function returning an async iterator)
and calls registered handlers for each message. It uses exponential backoff
with jitter on connection failures and supports graceful stop.
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, AsyncIterator, Awaitable, Callable, List

logger = logging.getLogger(__name__)

MessageHandler = Callable[[Any], Awaitable[None]] | Callable[[Any], None]


class WebSocketSupervisor:
    def __init__(
        self,
        connect_factory: Callable[[], AsyncIterator[Any]],
        *,
        min_backoff: float = 0.5,
        max_backoff: float = 30.0,
    ) -> None:
        self._connect_factory = connect_factory
        self._min_backoff = min_backoff
        self._max_backoff = max_backoff
        self._handlers: List[MessageHandler] = []
        self._task: asyncio.Task | None = None
        self._running = False

    def register_handler(self, handler: MessageHandler) -> None:
        self._handlers.append(handler)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run_loop(self) -> None:
        backoff = self._min_backoff
        while self._running:
            try:
                # connect_factory returns an async context manager (await to get it)
                cm = await self._connect_factory()
                async with cm as ws_iter:
                    logger.info({"event": "ws_connected"})
                    backoff = self._min_backoff
                    async for message in ws_iter:
                        await self._dispatch(message)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning({"event": "ws_error", "error": str(exc)})
                # Sleep with jitter and exponential backoff
                jitter = random.uniform(0, 0.25)
                await asyncio.sleep(min(backoff, self._max_backoff) + jitter)
                backoff = min(backoff * 2, self._max_backoff)

    async def _dispatch(self, message: Any) -> None:
        for h in list(self._handlers):
            try:
                result = h(message)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception("handler raised")
