# PR Draft: backend(MVP): Snapshot emission, liquidations snapshots, alert notifier, feed stubs

## Summary
This PR finalizes backend MVP work for TickerTape:

- Snapshot emission scheduler and Parquet writer with DatasetRegistry
- LiquidationsFeed: KPIs, top-K, cascade/velocity detection
- Feed stubs: Orderbook L2, FundingRates, Whale feed (schemas + registry placeholders)
- AlertManager wired to a local `SocketNotifier` (TCP JSON-lines) + example client
- Query helpers for frontend (dataset discovery, latest snapshot, recent events)
- CLI runner for snapshot emission (`tools/run_ingestion.py --profile liquidations_dashboard --once`)
- Tests and documentation added/updated

## Commits
- feat: finalize snapshot emission and parquet persistence
- feat: complete liquidations feed logic (KPIs, top-K, cascade detection)
- feat: add vision-referenced feed stubs (orderbook_l2, funding_rates, whale_trades)
- feat: wire AlertManager to SocketNotifier (TCP JSON-lines); add example client and tests
- feat: add frontend query helpers; docs; README updates; CLI and gate fixes

## Testing & Verification
Run from repo root:

```bash
# Data integrity gate (scopes to TickerTape via root config)
python tools/data_integrity_gate.py --ci --root .

# TickerTape tests
pytest -q tests

# Emit snapshots once (writes to data/parquet and updates registry)
python tools/run_ingestion.py --profile liquidations_dashboard --once
```

All checks passed during local validation and the TickerTape test suite is green.

## Notes for reviewer
- `alerts.SocketNotifier` is TCP JSON-lines for local development. If you prefer WebSockets, we can add a WS notifier in a follow-up (no code depending on that yet).
- Parquet write uses `pyarrow` if available; if not, a `.parquet.ndjson` fallback is used and query helpers handle both.
- Feeds are stubs with TODO comments for wiring real sources. Stubbing was intentional per Vision.

## Merge checklist
- [ ] Review code changes and tests
- [ ] Approve and merge into main
- [ ] Frontend team: begin integration using `query_helpers` and `examples/alert_client.py`

---

If you want, I can push this branch and open a draft PR (requires a remote 'origin'). Alternatively, I have created patch files under `../patches/` that you can apply and commit in any remote repository.
