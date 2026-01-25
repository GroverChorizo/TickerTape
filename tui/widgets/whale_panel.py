"""Whale activity panel."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ..backend.registry import get_registry
from ..backend.queries import recent_events
from ..state.datasets import load_datasets
from .panel_base import PanelBase
from .wallet_panel import WalletsDiscovered


class WhalePanel(PanelBase):
    def __init__(self) -> None:
        super().__init__(panel_id="whales", title="Whale Activity")

    def refresh_panel(self) -> None:
        registry = get_registry()
        datasets = load_datasets(registry)
        if "feed=whale_trades" not in datasets:
            self.update_text("Whale trades feed unavailable (stub or missing).")
            return
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        events = recent_events(registry, "feed=whale_trades", now_ms - 60 * 60 * 1000)
        if not events:
            self.update_text("No whale trade data available in the last hour.")
            return
        lines: List[str] = ["Recent whale trades (last hour):"]
        for event in events[-5:]:
            symbol = event.get("symbol", "?")
            side = event.get("side", "?")
            size = event.get("size", "?")
            price = event.get("price", "?")
            wallet = event.get("wallet") or event.get("wallet_address") or event.get("address")
            wallet_hint = f" wallet={wallet}" if isinstance(wallet, str) and wallet else ""
            lines.append(f"- {symbol} {side} size={size} price={price}{wallet_hint}")
        self.update_text("\n".join(lines))
        wallets = _extract_wallets(events)
        if wallets:
            self.post_message(WalletsDiscovered(wallets, source="whales"))


def _extract_wallets(events: List[dict]) -> List[str]:
    wallets: List[str] = []
    for event in events:
        for key in ("wallet", "wallet_address", "address"):
            value = event.get(key)
            if isinstance(value, str) and value:
                wallets.append(value)
    return wallets
