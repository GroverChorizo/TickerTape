# Day Trader Profile Specification

## Purpose

The Day Trader profile targets intraday traders who rely on price action and momentum.  The dashboard must provide a live, high‑density view of price movements, top positions and whale flows so traders can quickly identify opportunities without information overload.

## Functional Requirements

* **Data Streams** – Subscribe to real‑time tick data, positions and whale trade feeds from the Hyperliquid Data Layer API.  Traders must be able to maintain a fixed watchlist (BTC, ETH, SOL, etc.) while also scanning the broader universe for anomalies【438442747367044†L29-L35】.
* **Panels** – The Day Trader dashboard includes at least four core panels:
  1. **Price Chart** – Displays mini‑sparklines for BTC/ETH/SOL with trend indicators【438442747367044†L244-L252】.  Supports zoom and pan in fullscreen mode.
  2. **Top Positions** – Shows current long/short exposure with liquidation distance progress bars【438442747367044†L274-L283】.
  3. **Whale Flow** – Directional bar chart of large trades to track smart money【438442747367044†L384-L392】.
  4. **Liquidation Stats** – Heatmap of recent liquidation clusters and cascade risk【438442747367044†L371-L381】.
* **Watchlist Management** – Users can specify a watchlist via command (e.g., `:watchlist BTC,ETH,SOL`) and update or remove coins.  An anomaly detection function highlights unusual price or volume spikes【438442747367044†L155-L180】.
* **Alerts** – Optional alerts for whale trades, liquidation cascades and funding extremes are configurable from the settings panel【438442747367044†L40-L51】.

## Non‑Functional Requirements

* **Information Density** – Panel layouts must remain legible on screens as narrow as 80 columns, stacking panels vertically when space is limited【438442747367044†L590-L603】.
* **Responsiveness** – Support dynamic resizing: ultra‑wide (all panels visible) down to compact mode (single panel)【438442747367044†L551-L659】.
* **Reproducibility** – All data must be cached locally for consistent backtesting; no synthetic data may be introduced【980693054436426†L4-L11】.

## Implementation Notes

* The profile is registered under `profiles/day_trader.py` and returns a list of default panels and available commands.
* Use Pydantic or dataclasses to define tick and trade models.
* Use the command palette (`/`) to open panels, refresh data, and run searches.
* When the user presses `F`, the active panel should enter fullscreen mode to show extended data (e.g., 50 levels of order book)【438442747367044†L551-L659】.
