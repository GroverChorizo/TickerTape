"""Liquidations stats feed based on Hyperliquid endpoints."""
from __future__ import annotations

from typing import Any, Dict

from ..network import NetworkClient
from .base import BaseFeed


class LiquidationsStatsFeed(BaseFeed):
    def __init__(self, client: NetworkClient, offline: bool = False, poll_interval: float = 5.0) -> None:
        super().__init__(name="liquidations_stats", poll_interval=poll_interval, offline=offline)
        self.client = client

    def fetch(self) -> Dict[str, Any]:
        if self.offline:
            return {"status": "offline", "data": None}
        data = self.client.get("liquidations_stats")
        return {"status": "ok", "data": data}
