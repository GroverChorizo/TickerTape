"""Minimal async WebSocket supervisor with reconnect/backoff.

This module provides a small, dependency-free supervisor that accepts an
`async_connect` context factory (async function returning an async iterator)
and calls registered handlers for each message. It uses exponential backoff
with jitter on connection failures and supports graceful stop.
"""

from __future__ import annotations

import asyncio
import logging
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
        # Prefer attaching to the current running event loop; if none exists,
        # spawn a dedicated background thread with its own event loop so the
        # supervisor can be started from synchronous code (useful in tests).
        try:
            loop = asyncio.get_running_loop()
            self._task = loop.create_task(self._run_loop())
            self._bg_thread = None
            self._bg_loop = None
        except RuntimeError:
            # No running loop -> create background thread + loop
            import threading

            def _run_in_thread():
                loop = asyncio.new_event_loop()
                self._bg_loop = loop
                asyncio.set_event_loop(loop)
                try:
                    self._task = loop.create_task(self._run_loop())
                    loop.run_until_complete(self._task)
                except asyncio.CancelledError:
                    pass
                finally:
                    try:
                        loop.run_until_complete(loop.shutdown_asyncgens())
                    except Exception:
                        pass
                    loop.close()

            self._bg_thread = threading.Thread(target=_run_in_thread, daemon=True)
            self._bg_thread.start()

    async def stop(self) -> None:
        self._running = False
        # Cancel task on whichever loop is running it
        if getattr(self, "_bg_loop", None):
            try:
                # cancel the remote task
                if self._task and not self._task.done():
                    asyncio.run_coroutine_threadsafe(self._cancel_task(self._task), self._bg_loop).result(timeout=5)
            except Exception:
                pass
            # join the thread
            try:
                if getattr(self, "_bg_thread", None):
                    self._bg_thread.join(timeout=2)
            except Exception:
                pass
            self._task = None
            self._bg_loop = None
            self._bg_thread = None
        else:
            if self._task:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
                self._task = None

    async def _cancel_task(self, task: asyncio.Task) -> None:
        try:
            task.cancel()
            await task
        except asyncio.CancelledError:
            pass

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
                # If the stream ended cleanly, avoid a tight reconnect loop.
                # Treat a graceful close like a soft backoff to keep the loop responsive.
                if self._running:
                    # Use min_backoff regardless of whether we saw messages; prevents
                    # hot loops in tests when an iterator yields no messages.
                    await asyncio.sleep(self._min_backoff)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning({"event": "ws_error", "error": str(exc)})
                # Sleep with jitter and exponential backoff
                jitter = min(backoff * 0.1, 0.25)
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
