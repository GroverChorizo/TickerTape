# Research Reviewer Playbook

## Purpose
Review changes for correctness, determinism, and compliance with core values. Focus on risks, gaps, and regressions.

## Guardrails
- No financial advice or live trading defaults.
- No synthetic data in production paths.
- Deterministic outputs required for all research workflows.
- Local-only data and artifacts.

## Review Checklist
- Specs alignment with `PRD.md` and Vision files.
- Deterministic backtests with fixed seeds.
- Input validation coverage and error handling.
- Alerts and metrics use documented formulas.
- Tests cover critical paths and failure modes.

## Deliverable
Provide a concise review summary with:
- Severity-ranked issues.
- Missing tests or validation steps.
- Assumptions and open questions.

