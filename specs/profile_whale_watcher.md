# Whale Watcher Profile Specification

## Purpose

The Whale Watcher profile is tailored to users who track large orders and wallet flows to gauge smart‑money sentiment.  It aggregates high‑notional trades and displays directional flow patterns to identify accumulation or distribution phases.

## Functional Requirements

* **Data Streams** – Subscribe to “whale trade” streams from the Hyperliquid Data Layer API and optionally ingest external on‑chain wallet data if available.  Each event must include timestamp, asset, size, price and direction.
* **Panels** –
  1. **Whale Trade List** – A table of recent large trades (e.g., >$500k) with live updates.  New rows flash briefly (green for buys, red for sells) to draw attention【438442747367044†L784-L799】.
  2. **Directional Flow Bars** – A bar chart summarising net flows per asset with arrow density and thickness indicating conviction【438442747367044†L384-L392】.
  3. **Whale Heatmap** – Optional heatmap of whale activity by time and price level to detect clusters.
* **Alerts** – Users can set thresholds for whale trade size (e.g., >$500k) and receive pop‑up or audio alerts【438442747367044†L40-L51】.
* **Wallet Inspection** – Selecting a wallet address (e.g., from the trade list) opens a separate screen showing recent transactions, assets held and P&L summary as defined in theVision【438442747367044†L1768-L1773】.  This context varies by source panel (whale feed, liquidation feed, depositor list).

## Non‑Functional Requirements

* **Smooth Animations** – When a new trade arrives, animate row insertion and highlight using CSS classes (e.g., `.pulse-green` for buys, `.pulse-red` for sells)【438442747367044†L784-L799】.
* **Scalability** – Support thousands of events per minute without UI lag; summarise flows in aggregated panels when volume is high.
* **Determinism** – Ensure that event ordering is consistent across runs; use local caching for test fixtures.

## Implementation Notes

* Profile metadata is registered in `tui/state/profiles.py`; the screen implementation lives in `tui/ui/screens/profile_whale_watcher.py` (exported via the `profiles` facade).
* Provide commands to filter trades by symbol, size or side (`/search btc >1M sell`)【438442747367044†L1719-L1727】.
* The wallet inspection feature should reuse components from the global wallet panel to avoid duplication.
