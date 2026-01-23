# Strategy Implementation Guide

This guide explains how users integrate their own Python research logic into the Hyperliquid Quant Terminal. All strategy code is research-only and executed locally.

---

## 1. Philosophy of User-Supplied Strategy Code
- Strategies are for research, validation, and analysis only
- No live trading, order execution, or external network access
- All logic must be deterministic and reproducible

## 2. Required Interfaces and Expectations
- Strategies must accept validated, time-aligned market data (see Vision)
- Inputs: Pandas DataFrame(s) with required columns (OHLCV, signals, etc.)
- Outputs: Signal DataFrame, trade list, and/or metrics dictionary
- All interfaces are implementation-defined; see Vision for required columns and formats

## 3. Strategy Lifecycle
- **Loading:** User supplies Python code via local file or command
- **Validation:** System checks for required interfaces, type hints, and docstrings
- **Execution:** Strategy runs inside the backtest engine with no network access

## 4. Constraints
- No network access or external API calls
- No live execution or order routing
- All outputs must be deterministic given the same inputs
- No modification of historical data

## 5. Key Concepts
- **Signals:** Must be generated using only past and current data (no lookahead bias)
- **Orders:** Represent hypothetical research actions, not live trades
- **Position State:** Managed by the backtest engine; user code must not mutate engine state
- **Time Alignment:** All signals and orders must be aligned to data timestamps

## 6. Common Pitfalls
- Lookahead bias: Using future data to generate signals
- Data leakage: Allowing information from outside the research window
- Non-determinism: Randomness without fixed seed or reproducibility
- Interface mismatch: Missing required columns or outputs

---
For implementation details, see BtheVision_v1_5_5.txt, AGENTS.md, and playbooks.