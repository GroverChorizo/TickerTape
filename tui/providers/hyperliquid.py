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
