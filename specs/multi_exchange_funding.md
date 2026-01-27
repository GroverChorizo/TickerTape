# Multi‑Exchange Funding Rate Panel Specification

## Purpose

Extend the Funding Arbitrageur profile by comparing funding rates across multiple exchanges (Hyperliquid, Binance, Bybit, etc.) and highlighting arbitrage opportunities.  This panel complements the Hyperliquid funding heatmap and helps users assess cross‑venue spreads【438442747367044†L1620-L1636】.

## Functional Requirements

* **Data Sources** – Fetch funding rates from multiple exchanges at regular intervals (e.g., once per minute).  Use publicly available endpoints; do not require API keys.
* **Comparison Table** – Display funding rates side‑by‑side with columns for each exchange and computed spread【438442747367044†L1620-L1636】.  Include a column indicating whether an arbitrage exists and an expected profit estimate【438442747367044†L1656-L1672】.
* **Arbitrage Detection** – Implement logic to identify the lowest and highest rates, compute the spread and flag when spread >0.05 % (0.0005).  Display recommended “long” and “short” exchanges and annualised profit percentage【438442747367044†L1656-L1672】.
* **Alerts** – Notify users when a spread meets or exceeds the configured threshold.  Provide options to adjust the threshold and disable alerts per symbol.
* **User Controls** – Commands to add or remove exchanges and to refresh data.  Provide a UI to select which exchanges appear in the table.

## Non‑Functional Requirements

* **Privacy** – Do not store or transmit user credentials; all data is public and read‑only.
* **Determinism** – Given the same snapshot of funding rates, the panel should produce identical outputs and arbitrage recommendations.
* **Performance** – Fetching and rendering the comparison table should take less than 500 ms.

## Implementation Notes

* Implement the panel under `panels/multi_exchange_funding.py`.
* Use the detection algorithm provided in theVision; encapsulate it in a helper function (`detect_funding_arbitrage`)【438442747367044†L1656-L1672】.
* Provide tests with static rate fixtures to verify detection logic.
* Integrate this panel into the Funding Arbitrageur profile via a command (e.g., `:panel funding_cmp`).
