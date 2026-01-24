# Changelog

## 2026-01-23 — Harden Data Integrity Gate & Secrets handling
- Gate now strictly requires `scan_roots` and a `.data_integrity_gate.json` at the provided `--root`.
- Scanning is constrained to `src/`, `tests/`, and `docs/` under the configured root (no repo-wide fallbacks).
- Misconfiguration results in hard failure (RuntimeError) to avoid accidental scope expansion.
- Added secure secrets loader `src/backend/secrets.py` that loads from env var → explicit path → default external path outside repo.
- Tests added/updated; gate runs in CI as a merge-blocking job.
