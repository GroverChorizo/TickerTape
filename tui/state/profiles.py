"""Profile definitions and defaults for the TickerTape TUI."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class ProfileConfig:
    name: str
    label: str
    description: str
    focus_panels: List[str]
    default_panel_order: List[str]


DEFAULT_PANEL_ORDER = [
    "liquidations",
    "funding",
    "whales",
    "event_stream",
    "alerts",
    "research",
]


PROFILES: Dict[str, ProfileConfig] = {
    "day_trader": ProfileConfig(
        name="day_trader",
        label="Day Trader",
        description="Intraday monitoring: liquidations, funding, whales, live events.",
        focus_panels=["liquidations", "funding", "whales", "event_stream", "alerts"],
        default_panel_order=DEFAULT_PANEL_ORDER,
    ),
    "liquidation_hunter": ProfileConfig(
        name="liquidation_hunter",
        label="Liquidation Hunter",
        description="Stress indicators, cascades, and liquidations focus.",
        focus_panels=["liquidations", "event_stream", "alerts", "research"],
        default_panel_order=DEFAULT_PANEL_ORDER,
    ),
    "whale_watcher": ProfileConfig(
        name="whale_watcher",
        label="Whale Watcher",
        description="Large trade flow and accumulation/distribution focus.",
        focus_panels=["whales", "event_stream", "alerts", "research"],
        default_panel_order=DEFAULT_PANEL_ORDER,
    ),
    "funding_arbitrage": ProfileConfig(
        name="funding_arbitrage",
        label="Funding Arbitrage",
        description="Funding rate extremes, divergences, and positioning focus.",
        focus_panels=["funding", "liquidations", "event_stream", "alerts", "research"],
        default_panel_order=DEFAULT_PANEL_ORDER,
    ),
}


def list_profiles() -> List[ProfileConfig]:
    return list(PROFILES.values())


def get_profile(name: str) -> ProfileConfig:
    if name not in PROFILES:
        raise KeyError(f"Unknown profile: {name}")
    return PROFILES[name]


def default_profile() -> ProfileConfig:
    return PROFILES["day_trader"]
