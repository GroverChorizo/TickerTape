# TickerTape
## Hyperliquid Quant Terminal
### Institutional Research Platform

### an homage to the world's first stock data stream.

## Repository Scope
This repository contains the full codebase, documentation, and supporting infrastructure for the Hyperliquid Quant Terminal. It is designed as an institutional-grade, local-first quantitative research environment for crypto market analysis, backtesting, and data visualization. All code, data, and research artifacts remain local to the user's machine.

## Core Values
- **Privacy-first:** All user data, research, and exports are local-only. No cloud sync, no remote execution.
- **Precision:** Data integrity and reproducibility are enforced. No synthetic or modified history.
- **No advice:** The system does not provide financial advice, trade recommendations, or live trading capabilities.
- **Transparency:** All logic, metrics, and outputs are documented and reviewable.

## High-Level Architecture
- **Backend:** Data ingestion, engine logic, backtest/Monte Carlo, and research artifact management. No direct UI dependencies.
- **Frontend:** Textual TUI for dashboard, visualization, navigation, and command interface. No business logic or data mutation.

## Local-First Guarantees
- All data, exports, and execution are performed locally.
- No user data or IP leaves the machine.
- All research outputs (backtests, MC, logs) are stored locally and never uploaded.

## Development & Review Workflow
1. **Builder:** Implements features per theVision and playbooks.
2. **Reviewer:** Validates against Vision, PRD, and playbooks.
3. **Security Auditor:** Checks privacy, data integrity, and compliance with prohibitions.
4. **Data Integrity Gate:** Final check before merge/release.

## Canonical Specifications
- **Backend:** `WhaleWatch/QuanTT/BtheVision_v1_5_5.txt`
- **Frontend:** `WhaleWatch/QuanTT/FtheVision_v1_5_5.txt`
- **Core Values:** `AGENTS.md`
- **Role Playbooks:** `/playbooks/`
- **PR Template & Data Integrity Gate:** See `/tools/` and `/tests/`

---
This README is intentionally lightweight. For implementation details, see the Vision files and supporting documentation.


## Support the Project

If you find this project useful, you may support its continued development via:
- GitHub Sponsors
- One-time donations: BTC, XMR
- Contributions and feedback

Donations do not grant any special rights or commercial license.


## Licensing

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).

Commercial licenses are available for entities wishing to:
- embed this software in proprietary systems
- offer it as part of a commercial service
- distribute modified versions without open-sourcing changes

For commercial licensing inquiries, contact: elias@osgrovesolutions.com
