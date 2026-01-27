"""Wallet detail screen."""

from __future__ import annotations

from tui.ui.screens.base import BaseScreen


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
        self.body.update(
            "\n".join(
                [
                    f"Wallet: {self._address}",
                    "Data unavailable for this wallet in current feeds.",
                    "Use 'home' or 'profile whale_watcher' to return.",
                ]
            )
        )
