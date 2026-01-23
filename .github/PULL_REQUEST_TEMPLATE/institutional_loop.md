# PR Title: <clear, specific>

## 0) Scope (1–3 sentences)
What does this PR change? What does it NOT change?

## 1) Core Values Compliance (required)
- [ ] Data security first: local-first, no hidden network calls, exports local-only
- [ ] Precision: no synthetic data, no modified historical data, deterministic where applicable
- [ ] Normal people, institutional-grade tools: industry-standard logic, clear UX
- [ ] No financial advice anywhere (UI copy, docs, comments)

## 2) Builder Pass (Implementation) — REQUIRED
### A) Assumptions (explicit)
- Assumption 1:
- Assumption 2:

### B) Implementation Notes
- Modules touched:
- New modules:
- Config changes:

### C) Tests Added/Updated
- Unit tests:
- Edge cases:
- How to run:
  - `pytest -q` (or your command)

### D) Performance / Safety Notes
- Streaming update rate assumptions:
- Caching decisions:
- Failure modes & recovery:

---

## 3) Research Reviewer Pass — REQUIRED (Quant Rigor)
> Run the Research Reviewer checklist from `playbooks/research_reviewer.md`.

### Evidence Attached (required)
- [ ] No lookahead bias (signal->entry is next bar; no shift(-1) leaks)
- [ ] Costs modeled where relevant (commission/slippage/spread/impact)
- [ ] Robustness checks included where relevant (MC trade shuffle, WF degradation)
- [ ] Metrics validated (unit tests or known examples)

### Reviewer Notes
- Findings:
- Red flags:
- Required fixes (if any):
- Go/No-Go (research-only):
  - [ ] GO
  - [ ] NO-GO

---

## 4) Privacy & Security Auditor Pass — REQUIRED
> Run the Security checklist from `playbooks/privacy_security_auditor.md`.

### Audit Checks (required)
- [ ] No secret leakage in logs (keys/tokens/wallet-like strings redacted)
- [ ] No unsafe parsing (`eval`, `exec`, `pickle.loads` on untrusted input)
- [ ] No path traversal / uncontrolled filesystem writes
- [ ] Outbound requests are explicit, minimal, and documented

### Auditor Notes
- Threat model impact:
- Findings:
- Mitigations:
- Verification steps:
- Pass/Fail:
  - [ ] PASS
  - [ ] FAIL

---

## 5) Data Integrity Gate — REQUIRED
### Automated Checks
- [ ] `python tools/data_integrity_gate.py --ci` passes
- [ ] `pytest -q` passes (includes integrity tests)

### Notes (if any)
- Exceptions justified (must include rationale + scope + follow-up issue link):
