"""Hyperliquid provider over the direct HL HTTP client."""

from __future__ import annotations

from typing import Any, Dict, Optional
import time

from tui.feeds.hyperliquid import HyperliquidClient
from tui.models.liquidations import LiquidationSnapshot
from tui.models.market import MarketContext
from tui.feeds.base import FeedResult
from tui.feeds.liquidations import LiquidationsRadarFeed
from tui.feeds.market_data import MarketDataFeed
from tui.feeds.hyperliquid import FundingRatesFeed, WhaleTradesFeed, EventStreamFeed
from tui.feeds.smart_money import SmartMoneyFeed
from tui.feeds.hlp import HlpFeed
from tui.feeds.orderflow import OrderflowFeed
from tui.feeds.user_data import UserDataFeed
from tui.feeds.events_contracts import EventsContractsFeed
from tui.feeds.hip3 import Hip3Feed
from tui.feeds.whale_insights import WhaleInsightsFeed
from tui.feeds.positions import PositionsFeed
from tui.feeds.orderbook_depth import OrderbookDepthFeed
from backend.storage import DatasetRegistry


class HyperliquidProvider:
    def __init__(
        self,
        base_url: str = "https://api.hyperliquid.xyz",
        *,
        client: Optional[HyperliquidClient] = None,
        registry: Optional[DatasetRegistry] = None,
        offline: bool = False,
        datalayer: Optional[Any] = None,
    ) -> None:
        self._client = client or HyperliquidClient(base_url=base_url, datalayer=datalayer)
        self._registry = registry or DatasetRegistry()
        self._liquidations_feed = LiquidationsRadarFeed(
            self._client, registry=self._registry, offline=offline
        )
        self._market_feed = MarketDataFeed(
            self._client, registry=self._registry, offline=offline
        )
        # Optional streaming-enabled feeds (used when streamer pushes data)
        self._funding_feed = FundingRatesFeed(
            self._client, registry=self._registry, coins=["BTC"], offline=offline
        )
        self._whales_feed = WhaleTradesFeed(self._client, offline=offline)
        self._events_feed = EventStreamFeed(self._client, offline=offline)
        # Extended data-layer feeds (polling-based)
        self._smart_money_feed = SmartMoneyFeed(
            self._client, registry=self._registry, offline=offline
        )
        self._hlp_feed = HlpFeed(self._client, registry=self._registry, offline=offline)
        self._orderflow_feed = OrderflowFeed(
            self._client, registry=self._registry, offline=offline
        )
        self._user_data_feed = UserDataFeed(
            self._client, registry=self._registry, offline=offline
        )
        self._events_contracts_feed = EventsContractsFeed(
            self._client, registry=self._registry, offline=offline
        )
        self._hip3_feed = Hip3Feed(self._client, registry=self._registry, offline=offline)
        self._whale_insights_feed = WhaleInsightsFeed(
            self._client, registry=self._registry, offline=offline
        )
        self._positions_feed = PositionsFeed(
            self._client, registry=self._registry, offline=offline
        )
        self._orderbook_depth_feed = OrderbookDepthFeed(
            self._client, registry=self._registry, offline=offline
        )

    def close(self) -> None:
        self._client.close()

    def get_liquidations(self) -> FeedResult:
        result = self._liquidations_feed.fetch_result()
        if isinstance(result.data, dict):
            return FeedResult(
                status=result.status,
                data=LiquidationSnapshot.from_payload(result.data),
                error=result.error,
                updated_ts_ms=result.updated_ts_ms,
                is_lkg=result.is_lkg,
            )
        return result

    def get_market_context(self, symbol: str) -> FeedResult:
        if symbol:
            self._market_feed.set_selected_coin(symbol)
        result = self._market_feed.fetch_result()
        if isinstance(result.data, dict):
            return FeedResult(
                status=result.status,
                data=MarketContext.from_payload(result.data, symbol or ""),
                error=result.error,
                updated_ts_ms=result.updated_ts_ms,
                is_lkg=result.is_lkg,
            )
        return result

    def get_whales(self) -> FeedResult:
        return self._whales_feed.fetch_result()

    def get_funding(self) -> FeedResult:
        return self._funding_feed.fetch_result()

    def set_capture_enabled(self, enabled: bool) -> None:
        self._liquidations_feed.set_capture_enabled(enabled)

    def liquidation_next_delay(self, status: str) -> float:
        return self._liquidations_feed.next_delay(status)

    def market_next_delay(self, status: str) -> float:
        return self._market_feed.next_delay(status)

    def whales_next_delay(self, status: str) -> float:
        return self._whales_feed.next_delay(status)

    def funding_next_delay(self, status: str) -> float:
        return self._funding_feed.next_delay(status)

    def smart_money_next_delay(self, status: str) -> float:
        return self._smart_money_feed.next_delay(status)

    def hlp_next_delay(self, status: str) -> float:
        return self._hlp_feed.next_delay(status)

    def orderflow_next_delay(self, status: str) -> float:
        return self._orderflow_feed.next_delay(status)

    def user_data_next_delay(self, status: str) -> float:
        return self._user_data_feed.next_delay(status)

    def events_contracts_next_delay(self, status: str) -> float:
        return self._events_contracts_feed.next_delay(status)

    def hip3_next_delay(self, status: str) -> float:
        return self._hip3_feed.next_delay(status)

    def whale_insights_next_delay(self, status: str) -> float:
        return self._whale_insights_feed.next_delay(status)

    def positions_next_delay(self, status: str) -> float:
        return self._positions_feed.next_delay(status)

    def orderbook_depth_next_delay(self, status: str) -> float:
        return self._orderbook_depth_feed.next_delay(status)

    def get_smart_money(self) -> FeedResult:
        return self._smart_money_feed.fetch_result()

    def get_hlp(self) -> FeedResult:
        return self._hlp_feed.fetch_result()

    def get_orderflow(self, symbol: str | None = None) -> FeedResult:
        if symbol:
            self._orderflow_feed.set_symbol(symbol)
        return self._orderflow_feed.fetch_result()

    def get_user_data(self, address: str | None = None) -> FeedResult:
        if address is not None:
            self._user_data_feed.set_address(address)
        return self._user_data_feed.fetch_result()

    def get_events_contracts(self, address: str | None = None) -> FeedResult:
        if address is not None:
            self._events_contracts_feed.set_address(address)
        return self._events_contracts_feed.fetch_result()

    def get_hip3(self) -> FeedResult:
        return self._hip3_feed.fetch_result()

    def get_whale_insights(self) -> FeedResult:
        return self._whale_insights_feed.fetch_result()

    def get_positions_snapshot(self, symbol: str | None = None) -> FeedResult:
        if symbol:
            self._positions_feed.set_symbol(symbol)
        return self._positions_feed.fetch_result()

    def get_orderbook_depth(self, symbol: str | None = None) -> FeedResult:
        if symbol:
            self._orderbook_depth_feed.set_symbol(symbol)
        return self._orderbook_depth_feed.fetch_result()

    def diagnostics(self) -> Dict[str, Any]:
        report: Dict[str, Any] = {"http": "unknown", "ws": "not configured"}
        try:
            _ = self._client.get_json("liquidations_stats")
            report["http"] = "ok"
        except Exception as exc:
            report["http"] = f"error: {exc}"
        if callable(getattr(self._client, "ws_connect", None)):
            report["ws"] = "available"
        # include last-update timestamps when available
        last_updates: Dict[str, int] = {}
        for key, feed in (
            ("liquidations", self._liquidations_feed),
            ("market", self._market_feed),
            ("whales", self._whales_feed),
            ("funding", self._funding_feed),
            ("smart_money", self._smart_money_feed),
            ("hlp", self._hlp_feed),
            ("orderflow", self._orderflow_feed),
            ("user_data", self._user_data_feed),
            ("events_contracts", self._events_contracts_feed),
            ("hip3", self._hip3_feed),
            ("whale_insights", self._whale_insights_feed),
            ("positions_snapshot", self._positions_feed),
            ("orderbook_depth", self._orderbook_depth_feed),
        ):
            try:
                ts = feed.last_update_ts()
                if ts:
                    last_updates[key] = int(ts)
            except Exception:
                continue
        if last_updates:
            report["last_update_ms"] = max(last_updates.values())
            report["feeds"] = last_updates
        return report


class _PollContext:
    """Async context manager that yields a simple async iterator polling an HTTP endpoint."""

    def __init__(self, client, endpoint_key: str, params: dict | None = None, poll_interval: float = 2.0):
        self.client = client
        self.endpoint_key = endpoint_key
        self.params = params or {}
        self.poll_interval = poll_interval
        self._closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._closed = True
        return False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._closed:
            raise StopAsyncIteration
        import asyncio

        loop = asyncio.get_running_loop()

        def _sync_call():
            return self.client.get_json(self.endpoint_key, **(self.params or {}))

        result = await loop.run_in_executor(None, _sync_call)
        # yield result (could be dict/list depending on endpoint)
        await asyncio.sleep(0)  # allow context switch
        await asyncio.sleep(self.poll_interval)
        return result


class HyperliquidStreamer:
    """Wire HTTP polling-based streams into the existing TUI feeds.

    This is a pragmatic stepping-stone to true WebSocket streaming: it uses
    `WebSocketSupervisor` with a polling context factory (implemented above)
    to provide reconnect/backoff semantics and to push payloads into
    `LiquidationsRadarFeed` and `MarketDataFeed` via their `push()` method.
    """

    def __init__(self, provider: "HyperliquidProvider") -> None:
        from providers.ws import WebSocketSupervisor

        self.provider = provider
        self.supervisors: dict[str, "WebSocketSupervisor"] = {}
        self._client = provider._client

        # market aggregation: coalesce frequent tick/orderbook updates per-symbol
        # to avoid UI flooding. Keyed by symbol -> {"payload": ..., "task": Task}
        self._market_buffer: dict[str, dict] = {}
        # default aggregation window (milliseconds). Keep disabled by default to
        # preserve existing (immediate) behavior; enable via `start(..., market_agg_ms=...)`.
        self._market_agg_ms = 0
        # throttling: optional per-symbol minimum interval between pushes (seconds)
        self._market_min_interval_sec: float | None = None
        self._market_last_push: dict[str, float] = {}
        # shutdown coordination flag — prevents late/duplicate pushes during stop()
        self._stopping = False

    def start(self, *, poll_interval: float = 2.0, market_agg_ms: int | None = None, market_max_hz: float | None = None) -> None:
        """Start lightweight streaming for multiple endpoints.

        - `poll_interval` exists to make tests deterministic and to allow tuning.
        - `market_agg_ms` controls the coalescing window for high-frequency
          market updates (prices/orderbook).
        - `market_max_hz` optionally rate-limits market pushes per-symbol (Hz).
          If `None` no additional throttling is applied (aggregation still works).
        """ 
        # reset stopping flag so restarts work as expected
        self._stopping = False
        if market_max_hz is not None:
            try:
                hz = float(market_max_hz)
                if hz > 0:
                    self._market_min_interval_sec = 1.0 / hz
            except Exception:
                self._market_min_interval_sec = None
        else:
            self._market_min_interval_sec = None

        if market_agg_ms is not None:
            self._market_agg_ms = int(market_agg_ms)

        # Wire endpoints: liquidations (1h snapshot), whales, events, info (funding), plus market streams
        default_symbol = "BTC"
        try:
            default_symbol = getattr(self.provider, "_market_feed", None).selected_coin or "BTC"
        except Exception:
            default_symbol = "BTC"
        endpoints = [
            ("liquidations", {"timeframe": "1h"}, self._on_liquidations),
            ("whales", None, self._on_whales),
            ("events", None, self._on_events),
            ("info", None, self._on_info),
            # Market data: aggregated prices, per-symbol ticks and orderbook
            ("prices", None, self._on_market),
            ("ticks_latest", None, self._on_market),
            ("hip3_ticks_dex", {"dex": "hl", "ticker": "btc"}, self._on_market),
            ("orderbook", {"symbol": default_symbol}, self._on_market),
            # Funding: prefer dedicated funding endpoint when present
            ("binance_funding", None, self._on_info),
        ]
        from providers.ws import WebSocketSupervisor

        for key, params, handler in endpoints:
            # Prefer a native websocket connect factory if provided by the client.
            ws_factory = getattr(self._client, "ws_connect", None)

            if callable(ws_factory):
                # `ws_factory(endpoint_key, **params)` -> async context manager
                async def make_connect(k=key, p=params, wf=ws_factory):
                    import asyncio

                    maybe_cm = wf(k, **(p or {}))
                    if asyncio.iscoroutine(maybe_cm):
                        return await maybe_cm
                    return maybe_cm
            else:
                async def make_connect(k=key, p=params, pi=poll_interval):
                    return _PollContext(self._client, k, params=p, poll_interval=pi)

            sup = WebSocketSupervisor(connect_factory=make_connect, min_backoff=0.5, max_backoff=30.0)
            sup.register_handler(handler)
            sup.start()
            self.supervisors[key] = sup

    def stats(self) -> Dict[str, Dict[str, Any]]:
        """Return structured per-stream telemetry from supervisors."""
        now_ms = int(time.time() * 1000)
        telemetry: Dict[str, Dict[str, Any]] = {}
        for endpoint, supervisor in self.supervisors.items():
            if not hasattr(supervisor, "stats"):
                continue
            snapshot = supervisor.stats()
            last_msg = snapshot.last_message_ts_ms
            lag_ms = None if last_msg is None else max(0, now_ms - int(last_msg))
            telemetry[endpoint] = {
                "running": bool(snapshot.running),
                "connected": bool(snapshot.connected),
                "connect_count": int(snapshot.connect_count),
                "reconnect_count": int(snapshot.reconnect_count),
                "messages_received": int(snapshot.messages_received),
                "error_count": int(snapshot.error_count),
                "last_error": snapshot.last_error,
                "last_connect_ts_ms": snapshot.last_connect_ts_ms,
                "last_message_ts_ms": last_msg,
                "last_disconnect_ts_ms": snapshot.last_disconnect_ts_ms,
                "last_backoff_s": float(snapshot.last_backoff_s),
                "lag_ms": lag_ms,
            }
        return telemetry

    async def stop(self) -> None:
        # mark stopping so in-flight flushes avoid pushing
        self._stopping = True
        for sup in list(self.supervisors.values()):
            await sup.stop()
        self.supervisors = {}
        # Cancel and await pending market flush tasks to avoid races / warnings
        import asyncio

        pending = []
        other_loop_futs = []
        current_loop = asyncio.get_running_loop()
        for key, buf in list(self._market_buffer.items()):
            task = buf.get("task")
            task_loop = buf.get("loop") or getattr(task, "_loop", None)
            if not task or task.done():
                continue
            # If task lives on the current loop we can cancel+await directly
            if task_loop is current_loop:
                try:
                    task.cancel()
                except Exception:
                    pass
                pending.append(task)
                continue
            # Otherwise try to cancel/wait on the task's loop in a thread-safe way
            try:
                if hasattr(task_loop, "is_running") and task_loop.is_running():
                    # schedule cancellation on the owning loop
                    try:
                        task_loop.call_soon_threadsafe(task.cancel)
                    except Exception:
                        pass
                    # arrange to await the task on its loop and block briefly for it to finish
                    try:
                        fut = asyncio.run_coroutine_threadsafe(_await_task(task), task_loop)
                        other_loop_futs.append(fut)
                    except Exception:
                        # fall back to best-effort cancellation
                        pass
                else:
                    try:
                        task.cancel()
                    except Exception:
                        pass
            except Exception:
                pass
        # await tasks from the current loop normally
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        # wait (blocking) for any cross-loop futures to complete (short timeout)
        import concurrent.futures

        for fut in other_loop_futs:
            try:
                fut.result(timeout=1.0)
            except concurrent.futures.TimeoutError:
                # give up — best-effort cleanup
                pass
            except Exception:
                pass
        self._market_buffer.clear()

    async def _on_liquidations(self, message):
        # message expected to be dict (or JSON string) similar to fetch() result
        import json

        payload = message
        if isinstance(message, str):
            try:
                payload = json.loads(message)
            except Exception:
                payload = {"raw": message}
        try:
            self.provider._liquidations_feed.push(payload)
        except Exception:
            pass

    async def _on_whales(self, message):
        import json

        payload = message
        if isinstance(message, str):
            try:
                payload = json.loads(message)
            except Exception:
                payload = {"raw": message}
        payload = {"trades": payload} if not isinstance(payload, dict) or "trades" not in payload else payload
        try:
            if hasattr(self.provider, "_whales_feed"):
                self.provider._whales_feed.push(payload)
        except Exception:
            pass

    async def _on_events(self, message):
        import json

        payload = message
        if isinstance(message, str):
            try:
                payload = json.loads(message)
            except Exception:
                payload = {"raw": message}
        payload = {"events": payload} if not isinstance(payload, dict) or "events" not in payload else payload
        try:
            if hasattr(self.provider, "_events_feed"):
                self.provider._events_feed.push(payload)
        except Exception:
            pass

    async def _on_info(self, message):
        # mapping for info endpoint (used by funding rates)
        import json

        payload = message
        if isinstance(message, str):
            try:
                payload = json.loads(message)
            except Exception:
                payload = {"raw": message}
        try:
            if hasattr(self.provider, "_funding_feed"):
                # convert info payload into funding-like payload
                self.provider._funding_feed.push({"funding": payload})
        except Exception:
            pass

    async def _on_market(self, message):
        # generic handler for prices/orderbook/tick streams
        import json
        import asyncio
        import time

        payload = message
        if isinstance(message, str):
            try:
                payload = json.loads(message)
            except Exception:
                payload = {"raw": message}

        # derive a symbol key for coalescing (fallback to global)
        symbol = None
        if isinstance(payload, dict):
            if "tick" in payload and isinstance(payload["tick"], dict):
                symbol = payload["tick"].get("symbol")
            symbol = symbol or payload.get("symbol") or payload.get("coin")
        symbol_key = (str(symbol).upper() if symbol else "_GLOBAL")

        # Coalesce high-frequency updates per-symbol: keep the latest payload
        # and schedule a single push after the aggregation window.
        try:
            if not hasattr(self.provider, "_market_feed"):
                return

            buf = self._market_buffer.get(symbol_key)
            # Throttle: if aggregation is disabled and a min-interval is set, skip
            # producing a new flush task when the last push for this symbol was
            # more recent than the minimum interval.
            if buf is None:
                now = time.time()
                last = self._market_last_push.get(symbol_key)
                # If aggregation is disabled and throttling is enabled, enforce the
                # interval *before* scheduling the immediate flush to avoid a race
                # where multiple tasks are created before last_push is recorded.
                if self._market_agg_ms == 0 and self._market_min_interval_sec is not None:
                    if last is not None and (now - last) < self._market_min_interval_sec:
                        # drop this incoming tick to enforce rate limit
                        return
                    # reserve the slot immediately so subsequent ticks are dropped
                    try:
                        self._market_last_push[symbol_key] = now
                    except Exception:
                        pass
                # store latest payload and schedule flush
                loop = asyncio.get_running_loop()
                task = loop.create_task(self._market_flush_later(symbol_key, self._market_agg_ms / 1000.0))
                # record the loop so stop() can cancel/await it safely across loop boundaries
                self._market_buffer[symbol_key] = {
                    "payload": payload,
                    "task": task,
                    "loop": loop,
                    "ts": time.time(),
                }
            else:
                # overwrite latest payload (coalesce)
                buf["payload"] = payload
        except Exception:
            pass

    async def _market_flush_later(self, symbol_key: str, delay: float) -> None:
        import asyncio
        import time

        try:
            # small delays (0) should still yield to the loop
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return
        # If we're stopping, do not push any more updates
        if self._stopping:
            # ensure buffer entry is removed
            self._market_buffer.pop(symbol_key, None)
            return
        buf = self._market_buffer.pop(symbol_key, None)
        if not buf:
            return
        payload = buf.get("payload")
        try:
            if hasattr(self.provider, "_market_feed") and not self._stopping:
                self.provider._market_feed.push(payload)
                # record the push time for throttling
                try:
                    sym = (payload.get("tick") or payload).get("symbol") if isinstance(payload, dict) else None
                    key = (str(sym).upper() if sym else "_GLOBAL")
                    self._market_last_push[key] = time.time()
                except Exception:
                    pass
        except Exception:
            pass


async def _await_task(task):
    """Utility: await a Task on its owning loop (used with run_coroutine_threadsafe)."""
    try:
        await task
    except Exception:
        return
