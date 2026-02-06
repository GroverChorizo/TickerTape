# Data Ingestion & Provider Specification

## Purpose

Define the interfaces and responsibilities for ingesting real‑time and historical market data into the terminal.  The ingestion layer must abstract the Hyperliquid Data Layer API and any future sources, providing a consistent, typed interface for the UI and analysis engines.

## Functional Requirements

* **Provider Interface** – Implement a provider abstraction that defines methods for obtaining:
  - **Tick Data** – High‑frequency trade prices and volumes.
  - **Order Book Snapshots** – Top levels of the bid/ask depth.
  - **Liquidation Events** – Forced position closures with size, price and timestamp【438442747367044†L274-L283】.
  - **Whale Trades** – Large, high‑notional trades with direction【438442747367044†L384-L392】.
  - **Funding Rates** – Hourly funding rate values and formulas【438442747367044†L104-L116】.
  - **Positions** – User positions with size, entry price and liquidation price.
* **Snapshot + Streaming** – Each endpoint should support one‑time snapshot retrieval and a live streaming subscription via WebSocket; the provider must automatically reconnect and backoff on errors.
* **Caching** – Maintain an in‑memory and optional on‑disk cache of the most recent snapshot for each dataset to reduce network calls and support offline testing.
* **Typed Models** – Use Pydantic or dataclasses to define data models (e.g., `Tick`, `Liquidation`, `FundingRate`).  All timestamps must be timezone‑aware and monotonic.
* **Error Handling** – Implement timeouts, retries with jitter, and circuit‑breaker logic to ensure resilience【438442747367044†L104-L116】.

## Non‑Functional Requirements

* **Determinism** – When provided with the same timestamps and parameters, the provider must return identical data objects.
* **Local‑First** – No data is stored externally; all caching is local.  Exported data remains on the user’s machine【980693054436426†L14-L18】.
* **Performance** – Snapshot retrieval should complete within 200 ms under normal conditions; streaming latency should be sub‑200 ms.

## Implementation Notes

* Implement the provider in `providers/hyperliquid.py` with a configurable base URL and environment (e.g., testnet, mainnet).
* Future providers (e.g., Binance) should follow the same interface; implement discovery via `providers/__init__.py`.
* The TUI consumes provider data via feed adapters in `tui/providers/` and `tui/feeds/` for UI‑specific streaming/polling behavior.
* Provide diagnostic commands (e.g., `:diagnose provider`) that test HTTP and WebSocket connectivity and return a short report.
