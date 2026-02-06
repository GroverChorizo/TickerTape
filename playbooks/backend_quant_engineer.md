# Backend Quant Engineer Playbook

## Purpose
Build deterministic, local-first backend systems for data ingestion, validation, research jobs, and alerting. Do not produce financial advice or live trading functionality.

## Guardrails
- Keep all data and artifacts local-only. No external exports.
- No synthetic or modified historical data in production paths.
- No eval/exec of user-provided code without explicit confirmation and sandboxing.
- Deterministic results: same inputs + seed -> same outputs.

## Workflow
1. Confirm spec alignment with `BtheVision_v1_5_5.txt`, `PRD.md`, and `specs/`.
2. Define interfaces first (models, contracts, IO).
3. Implement with typed dataclasses, explicit error handling, and logging.
4. Add tests for correctness, determinism, and failure modes.
5. Run the Data Integrity Gate and relevant tests.

## Design Checklist
- Provider interfaces: snapshot + stream, cache and retry policy, typed models.
- Backtesting: no lookahead bias, explicit slippage/fees, deterministic seed.
- Provenance: metadata and result persistence under `~/.ticker_tape/`.
- Alerts: structured events, severity levels, local-only transport.

## Testing Checklist
- Unit tests cover happy path and error handling.
- Determinism test with fixed seed + dataset.
- No network calls in tests unless fully mocked.

