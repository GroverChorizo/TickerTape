"""Endpoint-aware URL builder for MoonDev Hyperliquid data feeds."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class EndpointSpec:
    path: str
    symbol_case: str | None = None
    ticker_case: str | None = None


ENDPOINT_SPECS: Dict[str, EndpointSpec] = {
    "liquidations_stats": EndpointSpec("/api/liquidations/stats.json"),
    "whales": EndpointSpec("/api/whales.json"),
    "prices": EndpointSpec("/api/prices"),
    "price": EndpointSpec("/api/price/{symbol}", symbol_case="upper"),
    "orderbook": EndpointSpec("/api/orderbook/{symbol}", symbol_case="upper"),
    "candles": EndpointSpec("/api/candles/{symbol}", symbol_case="upper"),
    "hip3_ticks": EndpointSpec("/api/hip3_ticks/{dex}_{ticker}.json", ticker_case="lower"),
    "binance_funding": EndpointSpec("/api/binance_funding.json"),
}


class EndpointUrlBuilder:
    """Builds endpoint URLs with endpoint-specific normalization rules."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def build(self, endpoint_key: str, **kwargs: Any) -> str:
        if endpoint_key not in ENDPOINT_SPECS:
            raise ValueError(f"Endpoint '{endpoint_key}' is not in allowlist")
        spec = ENDPOINT_SPECS[endpoint_key]
        params = dict(kwargs)
        if "symbol" in spec.path:
            symbol = params.get("symbol")
            if symbol is None:
                raise ValueError(f"Endpoint '{endpoint_key}' requires symbol")
            params["symbol"] = _normalize_case(symbol, spec.symbol_case)
        if "ticker" in spec.path:
            ticker = params.get("ticker")
            if ticker is None:
                raise ValueError(f"Endpoint '{endpoint_key}' requires ticker")
            params["ticker"] = _normalize_case(ticker, spec.ticker_case)
        path = spec.path.format(**params)
        return f"{self.base_url}{path}"


def _normalize_case(value: Any, mode: str | None) -> str:
    text = str(value).strip()
    if mode == "lower":
        return text.lower()
    if mode == "upper":
        return text.upper()
    return text
