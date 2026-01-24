# Backtest & Monte Carlo Engine Logic — Transparency Memo

This document provides a technical breakdown of the native backtest and Monte Carlo engines. All logic is implementation-defined per theVision and is designed for transparency, reproducibility, and local-only research.

---

## 1. Backtest Engine Design
- **Data Flow:** Ingests validated, time-aligned market data; no synthetic or modified history
- **Signal → Execution Timing:** Signals are acted on the next available bar; no lookahead bias
- **Cost Modeling:** All hypothetical trades include commission, slippage, and market impact per theVision
- **Position Lifecycle:** Positions are opened, managed, and closed according to research logic; all state transitions are logged

## 2. Monte Carlo Logic
- **Shuffling:** Only real, historical trade outcomes are shuffled; no fake or randomly generated trades
- **Assumptions Held Constant:** Trade statistics (win rate, average win/loss) are preserved; only order is randomized
- **Distributions:** Output distributions represent the range of possible outcomes given the same trade statistics

## 3. Determinism & Reproducibility
- All outputs are reproducible given the same inputs and random seed
- No modification or synthesis of historical data
- All randomization is controlled and logged

## 4. Explicit Non-Functions
- Engines do NOT execute live trades, route orders, or interact with exchanges
- Engines do NOT provide financial advice, recommendations, or strategy suggestions
- Engines do NOT modify, synthesize, or augment historical data

## 5. Known Limitations & Tradeoffs
- Results depend on quality and integrity of input data
- Monte Carlo analysis assumes independence of trade outcomes; regime shifts are not modeled
- Cost modeling is implementation-defined; see Vision for formulas
- All limitations are documented; see Vision and playbooks for details

---
For further details, see BtheVision_v1_5_5.txt, AGENTS.md, and playbooks.