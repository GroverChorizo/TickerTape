# Product Requirements Document (PRD)

## 1. Problem Statement
Quantitative researchers require a local-first, institutional-grade environment for analyzing crypto market data, validating research logic, and producing reproducible backtest and stress test results. The system must maximize information density, configurability, and transparency, while strictly prohibiting financial advice and live trading.

## 2. Non-Goals and Explicit Exclusions
- No live trading, order execution, or brokerage integration
- No financial advice, recommendations, or strategy suggestions
- No cloud sync, remote data storage, or external data export
- No synthetic or modified historical data
- No marketing, performance, or profitability claims

## 3. Core Product Principles
- **Privacy-first:** All user data and research remain local
- **Precision:** Data integrity and reproducibility are mandatory
- **Transparency:** All logic, metrics, and outputs are documented
- **No advice:** The system does not guide, recommend, or execute trades
- **Separation of concerns:** Backend and frontend responsibilities are strictly partitioned

## 4. Functional Requirements
- Ingest, cache, and display real-time and historical market data (see theVision)
- Provide configurable dashboards with high information density
- Support user-supplied Python research logic for backtesting and stress testing
- Implement institutional-grade backtest and Monte Carlo engines (see theVision)
- Enable local-only export of research artifacts (CSV, Parquet, JSON)
- Provide command-driven navigation and panel management
- Enforce input validation, error handling, and logging per playbooks

## 5. Non-Functional Requirements
- **Determinism:** All research outputs are reproducible given the same inputs
- **Performance:** Backtests complete within 10s; dashboard latency <500ms
- **Transparency:** All engine logic, metrics, and outputs are documented
- **Security:** No user data or IP leaves the machine; all secrets are local

## 6. User Personas
- **Quantitative Researcher:** Develops, tests, and validates research logic
- **Developer:** Contributes to engine, UI, or infrastructure per theVision and playbooks
- **Reviewer/Security Auditor:** Validates compliance with core values and prohibitions

## 7. Out-of-Scope Items
- Live trading, order routing, or execution
- Financial advice or recommendations
- Cloud-based features or remote data export
- Synthetic data generation or modification

---
For implementation details, see BtheVision_v1_5_5.txt, FtheVision_v1_5_5.txt, AGENTS.md, and playbooks.