"""Hyperliquid provider backed by MoonDev API."""

from __future__ import annotations

from typing import Any, Dict, Optional

from tui.feeds.moondev_client import MoonDevClient
from tui.models.liquidations import LiquidationSnapshot
from tui.models.market import MarketContext
from tui.feeds.base import FeedResult
from tui.feeds.liquidations import LiquidationsRadarFeed
from tui.feeds.market_data import MarketDataFeed
from backend.storage import DatasetRegistry


class HyperliquidProvider:
    def __init__(
        self,
        base_url: str = "https://api.moondev.com",
        *,
        client: Optional[MoonDevClient] = None,
        registry: Optional[DatasetRegistry] = None,
        offline: bool = False,
    ) -> None:
        self._client = client or MoonDevClient(base_url=base_url)
        self._registry = registry or DatasetRegistry()
        self._liquidations_feed = LiquidationsRadarFeed(
            self._client, registry=self._registry, offline=offline
        )
        self._market_feed = MarketDataFeed(
            self._client, registry=self._registry, offline=offline
        )

    def close(self) -> None:
        self._client.close()

    def get_liquidations(self) -> FeedResult:
        result = self._liquidations_feed.fetch_result()
        if isinstance(result.data, dict):
            result.data = LiquidationSnapshot.from_payload(result.data)
        return result

    def get_market_context(self, symbol: str) -> FeedResult:
        if symbol:
            self._market_feed.set_selected_coin(symbol)
        result = self._market_feed.fetch_result()
        if isinstance(result.data, dict):
            result.data = MarketContext.from_payload(result.data, symbol or "")
        return result

    def set_capture_enabled(self, enabled: bool) -> None:
        self._liquidations_feed.set_capture_enabled(enabled)

    def liquidation_next_delay(self, status: str) -> float:
        return self._liquidations_feed.next_delay(status)

    def market_next_delay(self, status: str) -> float:
        return self._market_feed.next_delay(status)

    def diagnostics(self) -> Dict[str, Any]:
        report: Dict[str, Any] = {"http": "unknown"}
        try:
            _ = self._client.get_json("liquidations_stats")
            report["http"] = "ok"
        except Exception as exc:
            report["http"] = f"error: {exc}"
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

    def start(self, *, poll_interval: float = 2.0) -> None:
        """Start lightweight streaming for multiple endpoints.

        The `poll_interval` parameter exists to make tests deterministic and to
        allow tuning in low-latency scenarios.
        """
        # Wire endpoints: liquidations (1h snapshot), whales, events, info (funding)
        endpoints = [
            ("liquidations", {"timeframe": "1h"}, self._on_liquidations),
            ("whales", None, self._on_whales),
            ("events", None, self._on_events),
            ("info", None, self._on_info),
        ]
        from providers.ws import WebSocketSupervisor

        for key, params, handler in endpoints:
            async def make_connect(k=key, p=params, pi=poll_interval):
                return _PollContext(self._client, k, params=p, poll_interval=pi)

            sup = WebSocketSupervisor(connect_factory=make_connect, min_backoff=0.5, max_backoff=30.0)
            sup.register_handler(handler)
            sup.start()
            self.supervisors[key] = sup

    async def stop(self) -> None:
        for sup in list(self.supervisors.values()):
            await sup.stop()
        self.supervisors = {}

    async def _on_liquidations(self, message):
        # message expected to be dict similar to fetch() result
        payload = message
        try:
            self.provider._liquidations_feed.push(payload)
        except Exception:
            pass

    async def _on_whales(self, message):
        payload = {"trades": message}
        try:
            if hasattr(self.provider, "_whales_feed"):
                self.provider._whales_feed.push(payload)
        except Exception:
            pass

    async def _on_events(self, message):
        payload = {"events": message}
        try:
            if hasattr(self.provider, "_events_feed"):
                self.provider._events_feed.push(payload)
        except Exception:
            pass

    async def _on_info(self, message):
        # mapping for info endpoint (used by funding rates)
        try:
            if hasattr(self.provider, "_funding_feed"):
                # convert info payload into funding-like payload
                self.provider._funding_feed.push({"funding": message})
        except Exception:
            pass
