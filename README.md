# Hyperliquid Quant Terminal — Institutional Research Platform

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
- **Backend:** `WhaleWatch/TickerTape/BtheVision_v1_5_5.txt`
- **Frontend:** `WhaleWatch/TickerTape/FtheVision_v1_5_5.txt`
- **Core Values:** `AGENTS.md`
- **Role Playbooks:** `/playbooks/`
- **PR Template & Data Integrity Gate:** See `/tools/` and `/tests/`

---
This README is intentionally lightweight. For implementation details, see the Vision files and supporting documentation.

Quick commands:

- Emit snapshots once (liquidations dashboard):

    python tools/run_ingestion.py --profile liquidations_dashboard --once

- Start example alert client:

    python examples/alert_client.py



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

## Secrets & Local Configuration (recommended) 🔐

- Recommended default (example only - do not treat as a real absolute path):
  - POSIX (Linux / macOS): `~/.tickertape/secrets/HLdontShare.env`
  - Windows (PowerShell / CMD): `%USERPROFILE%\.tickertape\secrets\HLdontShare.env`

- Loading order (safe & repeatable):
  1. Environment variables (explicit values or a path to a secrets file via `HL_DONT_SHARE_PATH` or `TICKERTAPE_SECRETS_PATH`)
  2. A secrets file located at the default external path shown above (outside the repository)

Note: The file above is an example pattern only. Do not commit real secrets into the repository; always keep `HLdontShare.env` outside the repo and/or load secrets via environment variables.

---

## How to run the Data Integrity Gate & tests (nested workspace)

- Run the gate (CI mode, scanning `TickerTape`):

```
python tools/data_integrity_gate.py --ci --root TickerTape
```

- Run the gate + tests (recommended canonical sequence from workspace root):

```
python tools/data_integrity_gate.py --ci --root TickerTape && (cd TickerTape && pytest -q)
```

- Or run from within the TickerTape directory:

```
python ../tools/data_integrity_gate.py --ci --root . && pytest -q
```

These commands run the gate only against the `TickerTape` project subtree (src/, tests/, docs/ and top-level files) and then run the test suite for the project.

**CI enforcement:** The `Data Integrity Gate` runs as part of the repository GitHub Actions CI and blocks merges on failures via the `data_integrity_gate.yml` workflow for `WhaleWatch/TickerTape`.
