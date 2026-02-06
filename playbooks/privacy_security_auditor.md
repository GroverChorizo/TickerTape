# Privacy & Security Auditor Playbook

## Purpose
Validate local-first guarantees, secrets handling, and data integrity safeguards.

## Guardrails
- No data leaves the machine; exports are local-only.
- No secret values in logs.
- No unsafe dynamic execution on untrusted inputs without confirmation.
- No synthetic/modified historical data in production paths.

## Audit Checklist
- Secrets path resolution and permissions.
- Logging redaction and avoidance of secret leakage.
- Network policy adherence and endpoint allowlists.
- Data Integrity Gate passes with no production violations.
- Storage locations are user-local and documented.

## Deliverable
Summarize findings with:
- Critical risks or leaks.
- Remediation steps.
- Verification steps (tests/gate commands).

