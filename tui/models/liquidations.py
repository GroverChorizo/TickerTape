"""Typed models for liquidation data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


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

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "LiquidationEvent":
        return cls(
            ts_ms=int(payload.get("ts_ms") or 0),
            symbol=str(payload.get("symbol") or "?"),
            side=str(payload.get("side") or "unknown"),
            notional_usd=_coerce_float(payload.get("notional_usd")),
            price=_coerce_float(payload.get("price")),
            size=_coerce_float(payload.get("size")),
            source=str(payload.get("source") or "unknown"),
            liquidated_wallet=_coerce_str(payload.get("liquidated_wallet")),
        )


@dataclass(frozen=True)
class LiquidationRollup:
    window: str
    count: int
    notional: float
    long_count: int
    short_count: int
    long_notional: float
    short_notional: float

    @classmethod
    def from_dict(cls, window: str, payload: Dict[str, Any]) -> "LiquidationRollup":
        return cls(
            window=window,
            count=int(payload.get("count") or 0),
            notional=float(payload.get("notional") or 0.0),
            long_count=int(payload.get("long_count") or 0),
            short_count=int(payload.get("short_count") or 0),
            long_notional=float(payload.get("long_notional") or 0.0),
            short_notional=float(payload.get("short_notional") or 0.0),
        )


@dataclass(frozen=True)
class CascadeRisk:
    level: str
    score: float
    reason: str


@dataclass(frozen=True)
class CaptureStatus:
    enabled: bool
    dataset: str
    timeframe: str
    last_export_ts_ms: Optional[int]
    file_count: int
    total_bytes: int
    base_path: str

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "CaptureStatus":
        return cls(
            enabled=bool(payload.get("enabled")),
            dataset=str(payload.get("dataset") or ""),
            timeframe=str(payload.get("timeframe") or ""),
            last_export_ts_ms=_coerce_int(payload.get("last_export_ts_ms")),
            file_count=int(payload.get("file_count") or 0),
            total_bytes=int(payload.get("total_bytes") or 0),
            base_path=str(payload.get("base_path") or ""),
        )


@dataclass(frozen=True)
class LiquidationSnapshot:
    events: List[LiquidationEvent]
    rollups: Dict[str, LiquidationRollup]
    series_notional: List[float]
    series_count: List[float]
    cascade: CascadeRisk
    top_symbols: Dict[str, List[Dict[str, Any]]]
    errors: List[str]
    capture: CaptureStatus

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "LiquidationSnapshot":
        events = [
            LiquidationEvent.from_dict(e)
            for e in payload.get("events", [])
            if isinstance(e, dict)
        ]
        rollups = {
            key: LiquidationRollup.from_dict(key, data)
            for key, data in (payload.get("rollups", {}) or {}).items()
            if isinstance(data, dict)
        }
        series = payload.get("series", {}) or {}
        cascade_raw = payload.get("cascade", {}) or {}
        cascade = CascadeRisk(
            level=str(cascade_raw.get("level") or "LOW"),
            score=float(cascade_raw.get("score") or 0.0),
            reason=str(cascade_raw.get("reason") or ""),
        )
        capture_raw = payload.get("capture", {}) or {}
        capture = (
            CaptureStatus.from_dict(capture_raw)
            if isinstance(capture_raw, dict)
            else CaptureStatus.from_dict({})
        )
        return cls(
            events=events,
            rollups=rollups,
            series_notional=[float(v or 0.0) for v in (series.get("notional") or [])],
            series_count=[float(v or 0.0) for v in (series.get("count") or [])],
            cascade=cascade,
            top_symbols=payload.get("top_symbols", {}) or {},
            errors=payload.get("errors", []) or [],
            capture=capture,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "events": [event.__dict__ for event in self.events],
            "rollups": {key: rollup.__dict__ for key, rollup in self.rollups.items()},
            "series": {
                "notional": list(self.series_notional),
                "count": list(self.series_count),
            },
            "cascade": self.cascade.__dict__,
            "top_symbols": self.top_symbols,
            "errors": list(self.errors),
            "capture": self.capture.__dict__,
        }


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
