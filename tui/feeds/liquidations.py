"""Liquidation radar feed for Liquidation Hunter profile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple
import time

from backend.storage import BASE_PARQUET_ROOT, DatasetRegistry, partition_and_write
from .base import BaseFeed


TIMEFRAMES = ("10m", "1h", "4h", "24h")
ROLLING_WINDOWS_MS = {
    "1m": 60_000,
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
}


@dataclass(frozen=True)
class LiquidationEvent:
    ts_ms: int
    symbol: str
    side: str
    notional_usd: Optional[float]
    price: Optional[float]
    size: Optional[float]
    source: str
    liquidated_wallet: Optional[str]


class LiquidationsRadarFeed(BaseFeed):
    def __init__(
        self,
        client: Any,
        *,
        registry: DatasetRegistry,
        poll_interval: float = 5.0,
        offline: bool = False,
    ) -> None:
        super().__init__(
            name="liquidations_radar", poll_interval=poll_interval, offline=offline
        )
        self.client = client
        self.registry = registry
        self.capture_enabled = False
        self._dataset_name = "liquidations_events"
        self._timeframe = "live"
        self._last_export_ts: Optional[int] = None
        self._last_export_files: int = 0
        self._last_export_bytes: int = 0

    def set_capture_enabled(self, enabled: bool) -> None:
        self.capture_enabled = enabled

    def fetch(self) -> Dict[str, Any]:
        now_ms = int(time.time() * 1000)
        error_messages: List[str] = []
        disconnect_flags: List[bool] = []
        timeframe_stats: Dict[str, Dict[str, Any]] = {}
        raw_events: List[Dict[str, Any]] = []

        for tf in TIMEFRAMES:
            try:
                raw = self.client.get_json("liquidations", timeframe=tf)
            except Exception as exc:
                error_messages.append(str(exc))
                disconnect_flags.append(isinstance(exc, (TimeoutError, OSError)))
                continue
            timeframe_stats[tf] = _normalize_timeframe_stats(raw)
            if tf == "1h":
                raw_events = _extract_event_list(raw)

        stats_payload: Dict[str, Any] = {}
        try:
            stats_payload = self.client.get_json("liquidations_stats")
        except Exception as exc:
            error_messages.append(str(exc))
            disconnect_flags.append(isinstance(exc, (TimeoutError, OSError)))

        if not raw_events:
            raw_events = _extract_largest_events(stats_payload)
        events = _normalize_events(raw_events, source="moondev")
        rollups = _compute_rollups(events, now_ms)
        series = _bucket_series(events, now_ms)
        cascade = _cascade_risk(rollups, series)
        top_symbols = {
            "5m": _top_symbols(events, now_ms, window_ms=ROLLING_WINDOWS_MS["5m"]),
            "15m": _top_symbols(events, now_ms, window_ms=ROLLING_WINDOWS_MS["15m"]),
            "24h": _top_symbols_from_stats(stats_payload),
        }
        capture = self._capture_if_enabled(events, now_ms)

        payload = {
            "timeframes": timeframe_stats,
            "events": [event.__dict__ for event in events],
            "rollups": rollups,
            "series": series,
            "cascade": cascade,
            "top_symbols": top_symbols,
            "errors": error_messages,
            "capture": capture,
        }
        if not events and not timeframe_stats and not stats_payload and error_messages:
            if disconnect_flags and all(disconnect_flags):
                raise ConnectionError("; ".join(error_messages))
            raise RuntimeError("; ".join(error_messages))
        return payload

    def _capture_if_enabled(
        self, events: List[LiquidationEvent], now_ms: int
    ) -> Dict[str, Any]:
        if self.capture_enabled and events:
            records = [event.__dict__ for event in events]
            try:
                partition_and_write(
                    self._dataset_name, self._timeframe, now_ms, records, self.registry
                )
                self._last_export_ts = now_ms
            except Exception:
                pass
        dataset_key = f"feed={self._dataset_name}"
        datasets = self.registry.list_datasets()
        parts = (
            datasets.get(dataset_key, {}).get("partitions", [])
            if isinstance(datasets, dict)
            else []
        )
        size_bytes = 0
        for part in parts:
            try:
                path = BASE_PARQUET_ROOT / part
                if path.exists():
                    size_bytes += path.stat().st_size
                else:
                    alt = path.with_suffix(path.suffix + ".ndjson")
                    if alt.exists():
                        size_bytes += alt.stat().st_size
            except Exception:
                continue
        self._last_export_files = len(parts)
        self._last_export_bytes = size_bytes
        return {
            "enabled": self.capture_enabled,
            "dataset": self._dataset_name,
            "timeframe": self._timeframe,
            "last_export_ts_ms": self._last_export_ts,
            "file_count": self._last_export_files,
            "total_bytes": self._last_export_bytes,
            "base_path": str(BASE_PARQUET_ROOT),
        }


def _extract_event_list(raw: Any) -> List[Dict[str, Any]]:
    if isinstance(raw, dict):
        events = (
            raw.get("liquidations")
            or raw.get("events")
            or raw.get("data")
            or raw.get("rows")
        )
        if isinstance(events, list):
            return [e for e in events if isinstance(e, dict)]
    if isinstance(raw, list):
        return [e for e in raw if isinstance(e, dict)]
    return []


def _extract_largest_events(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return []
    windows = raw.get("windows", {})
    window = (
        windows.get("24h", windows.get("4h", {})) if isinstance(windows, dict) else {}
    )
    largest = window.get("largest") if isinstance(window, dict) else None
    if isinstance(largest, list):
        return [e for e in largest if isinstance(e, dict)]
    return []


def _normalize_timeframe_stats(raw: Any) -> Dict[str, Any]:
    stats = raw.get("stats", raw) if isinstance(raw, dict) else {}
    return {
        "total_count": _first_int(stats, ["total_count", "count", "total"]),
        "total_notional": _first_float(
            stats,
            ["total_value_usd", "total_usd", "total_value", "total_volume", "total"],
        ),
        "long_count": _first_int(stats, ["long_count", "longs", "long_liqs"]),
        "short_count": _first_int(stats, ["short_count", "shorts", "short_liqs"]),
        "long_notional": _first_float(
            stats, ["long_value_usd", "long_usd", "long_value", "long_volume"]
        ),
        "short_notional": _first_float(
            stats, ["short_value_usd", "short_usd", "short_value", "short_volume"]
        ),
    }


def _normalize_events(
    raw_events: Iterable[Dict[str, Any]], source: str
) -> List[LiquidationEvent]:
    events: List[LiquidationEvent] = []
    for entry in raw_events:
        evt = _normalize_event(entry, source)
        if evt is not None:
            events.append(evt)
    events.sort(key=lambda e: e.ts_ms, reverse=True)
    return events


def _normalize_event(entry: Dict[str, Any], source: str) -> Optional[LiquidationEvent]:
    ts = _coerce_ts_ms(
        entry.get("timestamp_ms")
        or entry.get("timestamp")
        or entry.get("time")
        or entry.get("t")
    )
    symbol = _coerce_str(
        entry.get("symbol")
        or entry.get("coin")
        or entry.get("asset")
        or entry.get("ticker")
    )
    if not ts or not symbol:
        return None
    side_raw = _coerce_str(
        entry.get("side") or entry.get("direction") or entry.get("type") or ""
    )
    side = _normalize_side(side_raw)
    price = _coerce_float(entry.get("price") or entry.get("px"))
    size = _coerce_float(
        entry.get("size") or entry.get("sz") or entry.get("qty") or entry.get("amount")
    )
    notional = _coerce_float(
        entry.get("value_usd")
        or entry.get("usd_value")
        or entry.get("notional")
        or entry.get("value")
    )
    if notional is None and price is not None and size is not None:
        notional = price * size
    wallet = _coerce_str(
        entry.get("address") or entry.get("wallet") or entry.get("user")
    )
    return LiquidationEvent(
        ts_ms=ts,
        symbol=symbol,
        side=side,
        notional_usd=notional,
        price=price,
        size=size,
        source=source,
        liquidated_wallet=wallet,
    )


def _normalize_side(raw: Optional[str]) -> str:
    text = (raw or "").strip().lower()
    if text in {"long", "buy", "b", "longs", "long_liq"}:
        return "long_liq"
    if text in {"short", "sell", "s", "shorts", "short_liq"}:
        return "short_liq"
    return "unknown"


def _compute_rollups(
    events: List[LiquidationEvent], now_ms: int
) -> Dict[str, Dict[str, Any]]:
    rollups: Dict[str, Dict[str, Any]] = {}
    for label, window_ms in ROLLING_WINDOWS_MS.items():
        window = _filter_window(events, now_ms, window_ms)
        rollups[label] = _aggregate_events(window)
    return rollups


def _filter_window(
    events: List[LiquidationEvent], now_ms: int, window_ms: int
) -> List[LiquidationEvent]:
    start = now_ms - window_ms
    return [e for e in events if e.ts_ms >= start]


def _aggregate_events(events: List[LiquidationEvent]) -> Dict[str, Any]:
    total_notional = sum(e.notional_usd or 0.0 for e in events)
    long_events = [e for e in events if e.side == "long_liq"]
    short_events = [e for e in events if e.side == "short_liq"]
    long_notional = sum(e.notional_usd or 0.0 for e in long_events)
    short_notional = sum(e.notional_usd or 0.0 for e in short_events)
    return {
        "count": len(events),
        "notional": total_notional,
        "long_count": len(long_events),
        "short_count": len(short_events),
        "long_notional": long_notional,
        "short_notional": short_notional,
    }


def _bucket_series(
    events: List[LiquidationEvent],
    now_ms: int,
    *,
    window_ms: int = 15 * 60_000,
    bucket_ms: int = 60_000,
) -> Dict[str, List[float]]:
    start = now_ms - window_ms
    bucket_count = max(int(window_ms / bucket_ms), 1)
    totals = [0.0 for _ in range(bucket_count)]
    counts = [0.0 for _ in range(bucket_count)]
    for event in events:
        if event.ts_ms < start:
            continue
        idx = int((event.ts_ms - start) / bucket_ms)
        if 0 <= idx < bucket_count:
            totals[idx] += event.notional_usd or 0.0
            counts[idx] += 1.0
    return {"notional": totals, "count": counts}


def _cascade_risk(
    rollups: Dict[str, Dict[str, Any]], series: Dict[str, List[float]]
) -> Dict[str, Any]:
    counts = series.get("count", [])
    notional = series.get("notional", [])
    if len(counts) < 3:
        return {"level": "LOW", "score": 0.0, "reason": "insufficient data"}
    recent_count = counts[-1]
    recent_notional = notional[-1] if notional else 0.0
    baseline_counts = counts[-6:-1] if len(counts) >= 6 else counts[:-1]
    baseline_notional = notional[-6:-1] if len(notional) >= 6 else notional[:-1]
    avg_count = sum(baseline_counts) / max(len(baseline_counts), 1)
    avg_notional = sum(baseline_notional) / max(len(baseline_notional), 1)
    score = 0.0
    if avg_count > 0:
        score += (recent_count - avg_count) / avg_count
    if avg_notional > 0:
        score += (recent_notional - avg_notional) / avg_notional
    level = "LOW"
    if recent_count >= max(3.0, avg_count * 2) and recent_notional >= avg_notional * 2:
        level = "HIGH"
    elif (
        recent_count >= max(2.0, avg_count * 1.5)
        or recent_notional >= avg_notional * 1.5
    ):
        level = "MED"
    return {
        "level": level,
        "score": round(score, 2),
        "reason": f"last 1m count {int(recent_count)} vs avg {avg_count:.1f}",
    }


def _top_symbols(
    events: List[LiquidationEvent], now_ms: int, window_ms: int
) -> List[Dict[str, Any]]:
    window = _filter_window(events, now_ms, window_ms)
    bucket: Dict[str, Dict[str, Any]] = {}
    for event in window:
        stats = bucket.setdefault(
            event.symbol, {"symbol": event.symbol, "notional": 0.0, "count": 0}
        )
        stats["count"] += 1
        stats["notional"] += event.notional_usd or 0.0
    return sorted(
        bucket.values(), key=lambda item: item.get("notional", 0.0), reverse=True
    )


def _top_symbols_from_stats(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return []
    windows = raw.get("windows", {})
    window = (
        windows.get("24h", windows.get("4h", {})) if isinstance(windows, dict) else {}
    )
    by_coin = window.get("by_coin") or {}
    if not isinstance(by_coin, dict):
        return []
    rows: List[Dict[str, Any]] = []
    for symbol, data in by_coin.items():
        if not isinstance(data, dict):
            continue
        rows.append(
            {
                "symbol": symbol,
                "notional": _first_float(
                    data, ["total_value_usd", "total_value", "total_usd"]
                ),
                "count": _first_int(data, ["count", "total_count"]),
            }
        )
    return sorted(rows, key=lambda item: item.get("notional", 0.0), reverse=True)


def _first_float(source: Dict[str, Any], keys: Iterable[str]) -> Optional[float]:
    for key in keys:
        value = source.get(key)
        out = _coerce_float(value)
        if out is not None:
            return out
    return None


def _first_int(source: Dict[str, Any], keys: Iterable[str]) -> Optional[int]:
    for key in keys:
        value = source.get(key)
        out = _coerce_int(value)
        if out is not None:
            return out
    return None


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


def _coerce_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        text = str(value).strip()
    except Exception:
        return None
    return text or None


def _coerce_ts_ms(value: Any) -> Optional[int]:
    out = _coerce_int(value)
    if out is None:
        return None
    if out < 1_000_000_000_000:
        return out * 1000
    return out
