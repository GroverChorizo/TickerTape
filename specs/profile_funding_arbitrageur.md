# Funding Arbitrageur Profile Specification

## Purpose

The Funding Arbitrageur profile helps users monitor and exploit funding rate differentials across perpetual futures exchanges.  It highlights extreme funding on Hyperliquid and compares rates across multiple venues to identify arbitrage opportunities.

## Functional Requirements

* **Data Streams** – Subscribe to Hyperliquid funding rate updates and periodically fetch funding rates from other exchanges (e.g., Binance, Bybit).  The system must calculate and display the hourly funding rate formula for Hyperliquid【438442747367044†L104-L116】.
* **Panels** –
  1. **Funding Heatmap** – A time‑by‑asset heatmap showing funding rate history; coloured green/yellow/orange/red according to severity【438442747367044†L342-L359】.
  2. **Funding Extremes** – Displays current funding rate values with thresholds (e.g., ±0.05%, ±0.10%, ±0.15%) and triggers alerts when extremes are reached【438442747367044†L342-L359】.
  3. **Arbitrage Comparison** – A comparison table showing funding rates on Hyperliquid versus other exchanges, computed spread and whether an arbitrage exists【438442747367044†L1620-L1636】.  Use the detection logic provided in theVision to flag opportunities【438442747367044†L1656-L1672】.
* **Alerts** – Configurable thresholds for extreme funding; notify users when arbitrage conditions exceed 0.05 % and compute expected annualised profit【438442747367044†L1656-L1672】.

## Non‑Functional Requirements

* **Real‑time Accuracy** – Funding data must be refreshed at least once per minute and updated instantly when events occur; handle rate‑limit or API failures gracefully.
* **Privacy** – No external exchange credentials should be stored; use public endpoints only.
* **Determinism** – Arbitrage detection logic must produce the same results for the same snapshot of rates.

## Implementation Notes

* Create this profile in `profiles/funding_arbitrageur.py`.
* Use typed models for `FundingRate` and `ArbitrageOpportunity` to ensure schema consistency.
* Provide commands to add or remove exchanges (e.g., `:exchange add binance`).
* Keep the multi‑exchange comparison panel optional for users who only trade on Hyperliquid.
