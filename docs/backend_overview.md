# Backend Overview

This document enumerates the backend feeds, snapshot timeframes, KPIs, and alert schema used by the TickerTape backend.

Feeds:
- liquidations_events (primary event stream)
- liquidations_snapshots (aggregated snapshots)
- orderbook_l2 (stub)
- funding_rates (stub)
- whale_trades (stub)

Snapshot timeframes supported: 10m, 1h, 4h, 24h

Snapshot KPIs:
- timeframe
- window_start_ts_ms
- window_end_ts_ms
- computed_at_ts_ms
- count
- total_notional
- side_counts
- side_notional
- top_symbols
- top_exchanges
- cascade_detected
- velocity_score
- run_id / provenance

Alert schema (JSON):
- alert_type: str (e.g., "liquidation_spike")
- severity: str ("low","medium","high")
- source_feed: str
- timestamp_ms: int
- payload: object (structured)

Canonical commands:
- `python tools/run_ingestion.py --profile liquidations_dashboard --once` - emit snapshots once
- Query helpers available in `src.backend.query_helpers` for frontend use.
