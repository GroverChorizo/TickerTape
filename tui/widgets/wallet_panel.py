"""Wallet selection and detail panels."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from rich.text import Text
from textual.message import Message
from textual.widgets import OptionList
from textual.widgets.option_list import Option

from .panel_base import PanelBase


class WalletsDiscovered(Message):
    def __init__(self, addresses: Iterable[str], source: str) -> None:
        super().__init__()
        self.addresses = list(dict.fromkeys(addresses))
        self.source = source


class WalletSelected(Message):
    def __init__(self, address: str, source: str) -> None:
        super().__init__()
        self.address = address
        self.source = source


class WalletPanel(OptionList):
    def __init__(self) -> None:
        super().__init__()
        self.border_title = "Wallets"
        self._sources: Dict[str, str] = {}
        self._set_empty()

    def _set_empty(self) -> None:
        self.clear_options()
        self.add_option(Option(Text("No wallet addresses available"), id="empty"))
        self.disable_option("empty")

    def update_wallets(self, addresses: Iterable[str], source: str) -> None:
        unique = list(dict.fromkeys(addr for addr in addresses if addr))
        if not unique:
            self._set_empty()
            return
        self.clear_options()
        for addr in unique:
            self._sources[addr] = source
            self.add_option(Option(Text(addr), id=addr))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        address = str(event.option.id)
        if address == "empty":
            return
        source = self._sources.get(address, "unknown")
        self.post_message(WalletSelected(address, source))


class WalletDetailPanel(PanelBase):
    def __init__(self) -> None:
        super().__init__(panel_id="wallet_detail", title="Wallet Detail")
        self.update_text("No wallet selected.")

    def update_wallet(self, address: str, source: str) -> None:
        lines = [
            f"Wallet: {address}",
            f"Source panel: {source}",
            "Data unavailable for this wallet in the current backend feeds.",
        ]
        self.update_text("\n".join(lines))
