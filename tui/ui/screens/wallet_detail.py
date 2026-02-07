"""Wallet detail screen."""

from __future__ import annotations

from tui.ui.screens.base import BaseScreen
from tui.feeds.user_data import UserDataFeed
from tui.feeds.hyperliquid import HyperliquidClient
from backend.storage import DatasetRegistry
from tui.feeds.base import FeedResult


class WalletDetailScreen(BaseScreen):
    def __init__(self, address: str, source: str) -> None:
        super().__init__(
            screen_id="wallet_detail",
            title="Wallet Detail",
            context="wallet",
        )
        self._address = address
        self._source = source

    def on_mount(self) -> None:
        self.set_header("Wallet Detail")
        self.set_status(f"Source: {self._source}")
        registry = DatasetRegistry()
        feed = UserDataFeed(
            HyperliquidClient(),
            registry=registry,
            address=self._address,
            poll_interval=10.0,
        )
        result = feed.fetch_result()
        lines = _render_wallet_detail(self._address, result)
        self.body.update("\n".join(lines))


def _render_wallet_detail(address: str, result: FeedResult) -> list[str]:
    lines: list[str] = [f"Wallet: {address}"]
    if result.status != "ok":
        if result.error:
            lines.append(f"Status: {result.status} | {result.error}")
        else:
            lines.append(f"Status: {result.status}")
    payload = result.data if isinstance(result.data, dict) else None
    if not payload:
        lines.append("No user data available yet.")
        lines.append("Use 'home' or 'profile whale_watcher' to return.")
        return lines
    account = payload.get("account")
    positions = payload.get("positions")
    fills = payload.get("fills")
    if account:
        lines.append("Account snapshot available.")
    if positions:
        lines.append("Positions available.")
    if fills:
        lines.append("Recent fills available.")
    lines.append("Use 'home' or 'profile whale_watcher' to return.")
    return lines
