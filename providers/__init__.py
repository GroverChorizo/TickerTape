"""Provider package scaffolding."""

from pathlib import Path
import sys

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from .base import Provider
from .hyperliquid import DirectHyperliquidClient, HyperliquidProvider
from .models import (
    FundingRate,
    LiquidationEvent,
    OrderBookLevel,
    OrderBookSnapshot,
    Position,
    Tick,
    WhaleTrade,
)

__all__ = [
    "FundingRate",
    "DirectHyperliquidClient",
    "HyperliquidProvider",
    "LiquidationEvent",
    "OrderBookLevel",
    "OrderBookSnapshot",
    "Position",
    "Provider",
    "Tick",
    "WhaleTrade",
]
