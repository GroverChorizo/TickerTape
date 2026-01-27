# Liquidation Hunter Profile Specification

## Purpose

The Liquidation Hunter profile is designed for traders focused on detecting and capitalising on liquidation cascades in the perpetual futures markets.  It surfaces risk clusters, monitors distance to liquidation, and alerts users when cascading events begin.

## Functional Requirements

* **Data Streams** – Subscribe to liquidation feeds and position snapshots from the Hyperliquid Data Layer API.  Poll the user’s own open positions to compute distance‑to‑liquidation values and track cascading volumes【438442747367044†L274-L283】.
* **Panels** – The dashboard exposes:
  1. **Liquidation Heatmap** – A price‑by‑time heatmap showing recent liquidation clusters to spot cascades【438442747367044†L371-L381】.
  2. **Liquidation Distance** – Progress bars for each position representing percentage distance to liquidation; colour‑coded by risk (green >10 %, yellow 5–10 %, orange 3–5 %, red <3 %)【438442747367044†L274-L289】.
  3. **Cascade Monitor** – Displays total volume liquidated in the last 5 seconds and triggers an alert when a predefined threshold is exceeded.  The example code in theVision shows how to notify on cascades using Textual reactive fields【438442747367044†L62-L89】.
* **Alerts** – Configurable thresholds for cascade detection (e.g., >$300M in 5 s) generate pop‑up alerts and highlight affected panels【438442747367044†L62-L89】.
* **Watchlist** – Users can include specific tickers; the profile must still compute cascade risk for all tracked assets.

## Non‑Functional Requirements

* **Real‑time Updates** – Stream liquidation data via WebSocket where available; fall back to polling with exponential backoff on errors【438442747367044†L104-L116】.
* **Performance** – UI updates should not exceed 500 ms latency during cascades; progress bars must smoothly animate.
* **Determinism** – Cascade detection logic must be reproducible and deterministic; test with fixed fixtures to avoid flakiness.

## Implementation Notes

* The profile is defined in `profiles/liquidation_hunter.py`.  Use typed models for positions and liquidation events.
* Implement a `detect_cascade(volume_history: List[float], threshold: float) -> bool` helper with tests.
* Alerts should be routed to the global alert system with severity levels (warning, critical).  Use the alert threshold table provided in theVision【438442747367044†L842-L849】.
