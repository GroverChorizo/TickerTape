**PR Title:** Harden Data Integrity Gate scoping + add secure secrets loader

## Summary
This PR hardens the Data Integrity Gate by scoping integrity scans to a configured repo root and removing all fallback scanning behaviors. It also introduces a safe, repeatable secrets loader for TickerTape that loads from (1) environment variables, (2) an explicit path, or (3) a default external path outside the repository.

## Why this change
- Prevent accidental or malicious scans of unrelated repositories or parent directories.
- Enforce the invariant that integrity checks only operate inside a single configured project root.
- Keep secrets outside the repository and out of logs.

## Behavioral changes
- `tools/data_integrity_gate.py` now requires `.data_integrity_gate.json` at the provided `--root` and a `scan_roots` config.
- The gate will raise a hard error if misconfigured (missing config or no valid scan_roots).
- The gate ignores simulation language in `tests/` and `docs/`, and ignores full-line Python comments.
- Added `WhaleWatch/TickerTape/src/backend/secrets.py` and tests. Secrets are not logged and are loaded from outside the repo by default.

## How to run locally
- Run gate (CI mode) on TickerTape:

```bash
python tools/data_integrity_gate.py --ci --root WhaleWatch/TickerTape
```

- Gate + tests:

```bash
python tools/data_integrity_gate.py --ci --root WhaleWatch/TickerTape && (cd WhaleWatch/TickerTape && pytest -q)
```

## Security model
- Secrets loader precedence: environment vars → explicit path (HL_DONT_SHARE_PATH / TICKERTAPE_SECRETS_PATH) → default external path (`~/.tickertape/secrets/HLdontShare.env`).
- Secrets are never auto-injected into `os.environ` by the loader; they are returned as a dict for caller-controlled use.
- No secret values are written to logs.

## Tests
- TickerTape unit tests updated/added; gate & tests pass locally.

## Changelog
- Added a concise changelog entry describing the change and the new failure modes.

---
Please review for correctness and enforcement strength. This change enforces a safety invariant and should be merged only after review and CI green.