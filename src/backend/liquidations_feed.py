"""Liquidations feed: buffering and snapshot computation.

- Buffer LiquidationEvent objects
- Compute snapshots per timeframe (10m, 1h, 4h, 24h)
- Export snapshot record dict suitable for Parquet/registry
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from collections import defaultdict, Counter
import uuid
import logging

from .models import LiquidationEvent

logger = logging.getLogger(__name__)

DEFAULT_CADENCE_SECONDS = {
    "10m": 10 * 60,
    "1h": 60 * 60,
    "4h": 4 * 60 * 60,
    "24h": 24 * 60 * 60,
}


class LiquidationsFeed:
    """Buffer liquidation events and compute snapshots."""

    def __init__(self) -> None:
        self._buffer: List[LiquidationEvent] = []

    def add_event(self, event: LiquidationEvent) -> None:
        """Append an event to the buffer."""
        self._buffer.append(event)
        logger.debug({"event": "liquidation_received", "symbol": event.symbol, "size": event.size})

    def clear_buffer(self) -> None:
        self._buffer = []

    def _events_in_window(self, start_ts_ms: int, end_ts_ms: int) -> List[LiquidationEvent]:
        return [e for e in self._buffer if start_ts_ms <= int(e.timestamp.timestamp() * 1000) < end_ts_ms]

    def compute_snapshot(self, timeframe: str, window_start_ts_ms: int, window_end_ts_ms: int, provenance: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Compute snapshot KPIs from buffered events in [window_start, window_end).

        Returns a dict with required fields.
        """
        events = self._events_in_window(window_start_ts_ms, window_end_ts_ms)
        count = len(events)
        total_notional = sum(e.size * e.price for e in events)
        side_counts = Counter(e.side for e in events)
        # convert to list of structs for Parquet compatibility
        side_counts_list = [{"side": k, "count": v} for k, v in side_counts.items()]

        side_notional = defaultdict(float)
        symbol_notional = defaultdict(float)
        exchange_notional = defaultdict(float)

        for e in events:
            side_notional[e.side] += e.size * e.price
            symbol_notional[e.symbol] += e.size * e.price
            exch = None
            if e.meta and isinstance(e.meta, dict):
                exch = e.meta.get("exchange")
            if exch:
                exchange_notional[exch] += e.size * e.price

        top_symbols = sorted(symbol_notional.items(), key=lambda x: x[1], reverse=True)[:10]
        top_exchanges = sorted(exchange_notional.items(), key=lambda x: x[1], reverse=True)[:10]

        side_notional_list = [{"side": k, "notional": v} for k, v in side_notional.items()]

        # simple cascade / velocity detection: compute events per 60s buckets and detect spikes
        buckets = defaultdict(int)
        for e in events:
            ts_min = int(e.timestamp.replace(second=0, microsecond=0).timestamp())
            buckets[ts_min] += 1
        counts = list(buckets.values())
        cascade_detected = False
        velocity_score = 0.0
        if counts:
            import statistics

            mean = statistics.mean(counts)
            stdev = statistics.pstdev(counts) if len(counts) > 1 else 0.0
            max_bucket = max(counts)
            velocity_score = (max_bucket - mean) / (stdev + 1e-9) if stdev > 0 else float(max_bucket - mean)
            if max_bucket >= max(5, mean + 3 * stdev):
                cascade_detected = True

        snapshot = {
            "timeframe": timeframe,
            "window_start_ts_ms": window_start_ts_ms,
            "window_end_ts_ms": window_end_ts_ms,
            "computed_at_ts_ms": int(datetime.now(timezone.utc).timestamp() * 1000),
            "count": count,
            "total_notional": total_notional,
            "side_counts": side_counts_list,
            "side_notional": side_notional_list,
            "top_symbols": [{"symbol": s, "notional": n} for s, n in top_symbols],
            "top_exchanges": [{"exchange": e, "notional": n} for e, n in top_exchanges],
            "cascade_detected": cascade_detected,
            "velocity_score": velocity_score,
            "run_id": provenance.get("run_id") if provenance else str(uuid.uuid4()),
            "provenance": provenance or {},
        }
        logger.info({"event": "snapshot_computed", "timeframe": timeframe, "window_start": window_start_ts_ms, "count": count})
        return snapshot

    def compute_and_clear(self, timeframe: str, window_start_ts_ms: int, window_end_ts_ms: int, provenance: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        s = self.compute_snapshot(timeframe, window_start_ts_ms, window_end_ts_ms, provenance)
        # Optionally remove events in window from buffer (we keep for now to allow multiple timeframes)
        self._buffer = [e for e in self._buffer if int(e.timestamp.timestamp() * 1000) >= window_end_ts_ms]
        return s
