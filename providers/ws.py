"""Minimal async WebSocket supervisor with reconnect/backoff.

This module provides a small, dependency-free supervisor that accepts an
`async_connect` context factory (async function returning an async iterator)
and calls registered handlers for each message. It uses exponential backoff
with jitter on connection failures and supports graceful stop.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator, Awaitable, Callable, List, Optional

logger = logging.getLogger(__name__)

MessageHandler = Callable[[Any], Awaitable[None]] | Callable[[Any], None]


@dataclass(frozen=True)
class WebSocketSupervisorStats:
    running: bool
    connected: bool
    connect_count: int
    reconnect_count: int
    messages_received: int
    error_count: int
    last_error: Optional[str]
    last_connect_ts_ms: Optional[int]
    last_message_ts_ms: Optional[int]
    last_disconnect_ts_ms: Optional[int]
    last_backoff_s: float


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
        self._connected = False
        self._attempt_count = 0
        self._connect_count = 0
        self._reconnect_count = 0
        self._messages_received = 0
        self._error_count = 0
        self._last_error: Optional[str] = None
        self._last_connect_ts_ms: Optional[int] = None
        self._last_message_ts_ms: Optional[int] = None
        self._last_disconnect_ts_ms: Optional[int] = None
        self._last_backoff_s: float = 0.0

    def register_handler(self, handler: MessageHandler) -> None:
        self._handlers.append(handler)

    def stats(self) -> WebSocketSupervisorStats:
        return WebSocketSupervisorStats(
            running=self._running,
            connected=self._connected,
            connect_count=self._connect_count,
            reconnect_count=self._reconnect_count,
            messages_received=self._messages_received,
            error_count=self._error_count,
            last_error=self._last_error,
            last_connect_ts_ms=self._last_connect_ts_ms,
            last_message_ts_ms=self._last_message_ts_ms,
            last_disconnect_ts_ms=self._last_disconnect_ts_ms,
            last_backoff_s=self._last_backoff_s,
        )

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
        self._connected = False
        self._last_disconnect_ts_ms = int(time.time() * 1000)
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
            self._attempt_count += 1
            self._reconnect_count = max(0, self._attempt_count - 1)
            try:
                # connect_factory returns an async context manager (await to get it)
                cm = await self._connect_factory()
                async with cm as ws_iter:
                    logger.info({"event": "ws_connected"})
                    self._connected = True
                    self._connect_count += 1
                    self._last_connect_ts_ms = int(time.time() * 1000)
                    backoff = self._min_backoff
                    self._last_backoff_s = 0.0
                    async for message in ws_iter:
                        await self._dispatch(message)
                self._connected = False
                self._last_disconnect_ts_ms = int(time.time() * 1000)
                # If the stream ended cleanly, avoid a tight reconnect loop.
                # Treat a graceful close like a soft backoff to keep the loop responsive.
                if self._running:
                    # Use min_backoff regardless of whether we saw messages; prevents
                    # hot loops in tests when an iterator yields no messages.
                    self._last_backoff_s = self._min_backoff
                    await asyncio.sleep(self._min_backoff)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._connected = False
                self._last_disconnect_ts_ms = int(time.time() * 1000)
                self._error_count += 1
                self._last_error = str(exc)
                logger.warning({"event": "ws_error", "error": str(exc)})
                # Sleep with jitter and exponential backoff
                jitter = min(backoff * 0.1, 0.25)
                sleep_for = min(backoff, self._max_backoff) + jitter
                self._last_backoff_s = sleep_for
                await asyncio.sleep(sleep_for)
                backoff = min(backoff * 2, self._max_backoff)

    async def _dispatch(self, message: Any) -> None:
        self._messages_received += 1
        self._last_message_ts_ms = int(time.time() * 1000)
        for h in list(self._handlers):
            try:
                result = h(message)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception("handler raised")
