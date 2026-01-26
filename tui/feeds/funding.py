"""Multi-exchange funding feed for the TUI."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional
import logging
import time

from backend.storage import DatasetRegistry, partition_and_write
from backend.network import NetworkClient
from .base import BaseFeed
from .hyperliquid import _parse_funding_history, FundingPoint, HyperliquidClient

logger = logging.getLogger(__name__)


@dataclass
class FundingRow:
    exchange: str
    symbol: str
    rate: Optional[float]
    interval_hours: Optional[float]
    timestamp_ms: Optional[int]
    annualized_pct: Optional[float]
    status: str


class MultiExchangeFundingFeed(BaseFeed):
    def __init__(
        self,
        *,
        hyperliquid_client: NetworkClient,
        moondev_client: HyperliquidClient,
        registry: DatasetRegistry,
        coins: Optional[Iterable[str]] = None,
        poll_interval: float = 10.0,
        offline: bool = False,
        dataset_name: str = "funding_rates",
        timeframe: str = "live",
    ) -> None:
        super().__init__(name="funding", poll_interval=poll_interval, offline=offline)
        self.hyperliquid_client = hyperliquid_client
        self.moondev_client = moondev_client
        self.coins = [c.upper() for c in (coins or ["BTC", "ETH", "SOL"])]
        self._registry = registry
        self._dataset_name = dataset_name
        self._timeframe = timeframe

    def fetch(self) -> Dict[str, Any]:
        now_ms = int(time.time() * 1000)
        rows: List[FundingRow] = []
        errors: List[str] = []

        try:
            rows.extend(self._fetch_hyperliquid(now_ms))
        except Exception as exc:
            errors.append(f"Hyperliquid: {exc}")
            logger.warning({"event": "funding_hyperliquid_failed", "error": str(exc)})

        try:
            rows.extend(self._fetch_binance(now_ms))
        except Exception as exc:
            errors.append(f"Binance: {exc}")
            logger.warning({"event": "funding_binance_failed", "error": str(exc)})

        if not rows and errors:
            raise ConnectionError("; ".join(errors))

        payload = {
            "rows": [row.__dict__ for row in rows],
            "received_ts_ms": now_ms,
            "errors": errors,
        }
        self._persist_snapshot(payload, now_ms)
        return payload

    def _fetch_hyperliquid(self, now_ms: int) -> List[FundingRow]:
        end_ms = now_ms
        start_ms = end_ms - 60 * 60 * 1000
        rows: List[FundingRow] = []
        for coin in self.coins:
            history = self.hyperliquid_client.post(
                "info",
                {"type": "fundingHistory", "coin": coin, "startTime": start_ms},
            )
            points = _parse_funding_history(history)
            latest = points[-1] if points else None
            rows.append(
                _row_from_point(
                    exchange="Hyperliquid",
                    symbol=coin,
                    point=latest,
                    interval_hours=1.0,
                    now_ms=now_ms,
                )
            )
        return rows

    def _fetch_binance(self, now_ms: int) -> List[FundingRow]:
        raw = self.moondev_client.get_json("binance_funding")
        entries = _parse_binance_funding(raw)
        rows: List[FundingRow] = []
        for entry in entries:
            rows.append(
                _row_from_fields(
                    exchange="Binance",
                    symbol=entry.get("symbol"),
                    rate=entry.get("rate"),
                    interval_hours=entry.get("interval_hours"),
                    timestamp_ms=entry.get("timestamp_ms"),
                    now_ms=now_ms,
                )
            )
        return rows

    def _persist_snapshot(self, payload: Dict[str, Any], timestamp_ms: int) -> None:
        try:
            record = {
                "timestamp_ms": timestamp_ms,
                "rows": payload.get("rows", []),
            }
            partition_and_write(
                self._dataset_name,
                self._timeframe,
                timestamp_ms,
                [record],
                self._registry,
            )
        except Exception as exc:
            logger.warning({"event": "funding_snapshot_write_failed", "error": str(exc)})


def _parse_binance_funding(raw: Any) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    data = raw
    if isinstance(raw, dict):
        data = raw.get("data") or raw.get("funding") or raw.get("rates") or raw.get("items") or raw.get("results")
    if isinstance(data, dict):
        data = data.get("rows") or data.get("funding") or data.get("data") or list(data.values())
    if not isinstance(data, list):
        return entries
    for item in data:
        if not isinstance(item, dict):
            continue
        symbol = item.get("symbol") or item.get("coin") or item.get("asset") or item.get("pair")
        rate = item.get("funding_rate") or item.get("fundingRate") or item.get("rate") or item.get("r")
        interval = (
            item.get("interval_hours")
            or item.get("interval")
            or item.get("funding_interval_hours")
            or item.get("funding_interval")
        )
        timestamp = item.get("timestamp_ms") or item.get("timestamp") or item.get("time") or item.get("t")
        entries.append(
            {
                "symbol": str(symbol).upper() if symbol else None,
                "rate": _coerce_float(rate),
                "interval_hours": _coerce_float(interval),
                "timestamp_ms": _coerce_int(timestamp),
            }
        )
    return entries


def _row_from_point(
    *,
    exchange: str,
    symbol: str,
    point: Optional[FundingPoint],
    interval_hours: float,
    now_ms: int,
) -> FundingRow:
    rate = point.rate if point else None
    ts_ms = point.timestamp_ms if point else None
    annualized = _annualized(rate, interval_hours, exchange)
    status = _status_from_ts(ts_ms, interval_hours, now_ms)
    if rate is None:
        status = "ERROR"
    return FundingRow(
        exchange=exchange,
        symbol=symbol,
        rate=rate,
        interval_hours=interval_hours,
        timestamp_ms=ts_ms,
        annualized_pct=annualized,
        status=status,
    )


def _row_from_fields(
    *,
    exchange: str,
    symbol: Optional[str],
    rate: Optional[float],
    interval_hours: Optional[float],
    timestamp_ms: Optional[int],
    now_ms: int,
) -> FundingRow:
    interval = interval_hours or _default_interval_hours(exchange)
    annualized = _annualized(rate, interval, exchange)
    status = _status_from_ts(timestamp_ms, interval, now_ms)
    if rate is None:
        status = "ERROR"
    return FundingRow(
        exchange=exchange,
        symbol=symbol or "?",
        rate=rate,
        interval_hours=interval,
        timestamp_ms=timestamp_ms,
        annualized_pct=annualized,
        status=status,
    )


def _default_interval_hours(exchange: str) -> float:
    if exchange.lower() == "binance":
        return 8.0
    return 1.0


def _annualized(rate: Optional[float], interval_hours: Optional[float], exchange: str) -> Optional[float]:
    if rate is None:
        return None
    hours = interval_hours or _default_interval_hours(exchange)
    if hours <= 0:
        return None
    periods_per_day = 24.0 / hours
    return rate * periods_per_day * 365.0 * 100.0


def _status_from_ts(timestamp_ms: Optional[int], interval_hours: Optional[float], now_ms: int) -> str:
    if not timestamp_ms or not interval_hours:
        return "STALE"
    age_ms = max(now_ms - timestamp_ms, 0)
    limit_ms = interval_hours * 2 * 60 * 60 * 1000
    return "LIVE" if age_ms <= limit_ms else "STALE"


def _coerce_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
