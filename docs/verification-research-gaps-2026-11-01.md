# Executed verification — 1 November 2026

The four requirements from the supplied image are mapped to code, evidence and explicit boundaries in [research-gaps.md](research-gaps.md). Earlier verification is preserved in [verification-2026-10-21.md](verification-2026-10-21.md); its timings and claims describe that earlier run.

## Automated checks

**150 passed; 0 failed; 0 errors; 0 skipped**, in **66.37 seconds**. Command:

```powershell
.\venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --junitxml=artifacts/test-results.xml
```

The original 115 tests passed before implementation (53.53 seconds). The 35 added workspace cases cover:

- Authenticated assessment, four ERP profiles, configuration validation and real EXPLAIN ANALYZE evidence.
- Database-backed Admin authorization, analyst restrictions, explicit approval, rejection, repeated-approval rejection and prevention of client SQL substitution.
- Index comparison, persistence, report linkage, existing-index labels and atomic rollback after an injected write/DDL failure.
- Built-in date rewrite with complete result equivalence, including an empty reporting day.
- Real monthly partition creation, identical full source copies, partition pruning, null-date preservation, transactional cleanup and injected verification failure.
- Verified, repeatable order-header snapshots with live order/item/payment/ledger relationships preserved.
- Concurrent read/UPDATE comparisons with identical seeded operation lists; all per-operation report multisets and full copied data match across phases.
- Maximum supported eight workers with four writers; 48 operations per phase, including 24 updates. This is a bounded functionality check, not a load-capacity claim.
- Worker-failure and changed-result injections, durable failed decisions, successful retries and sandbox removal.
- JSON evidence export and Reports CSV references to workspace IDs/actions.

Tests run against automatically generated disposable PostgreSQL databases and remove those databases afterward. They do not replace the demo ERP dataset. The entire 150-test suite also retains the original connectivity, dataset-size, relational-integrity, security, query-safety, timeout, index-benchmark, archive, explorer, API and report checks.

Additional checks passed:

- `python -m pip check`: no broken requirements.
- Python compilation for application, models, routes, services, scripts and utilities.
- `node --check` for every file in `static/js`, including the new workspace UI.
- `scripts/init_db.py`: additive schema update successful; now 17 tables. Existing ERP rows preserved.
- `scripts/validate_dataset.py`: 77,220 ERP rows; all PK/FK, order/item arithmetic and payment-total checks passed.
- No remaining `erp_bench_` schemas after the executed experiments/tests; 14,000 live orders remain.
- `database/schema.sql` regenerated from the same SQLAlchemy model metadata, including `optimization_runs`.

## Browser verification

Checked the local app at http://127.0.0.1:5000/workspace with its existing local Admin account. Verified login, navigation, assessment completion, actual query plans, pending action cards, saved controls, full partition SQL, archive preview, administrator approval modal, successful query-rewrite verification, recorded decision history and evidence download. No warning/error console entries were reported for the checked workspace session.

The verified rewrite in demo assessment #2 returned the same 15 rows. Its three-repeat local comparison measured 1.973 ms before and 1.176 ms after (40.368% lower execution time). These are local observations, not expected production gains. Full samples/plans are in that assessment and its JSON download. The browser download completed as `erp-workspace-2.json`. Visual proof is saved at `artifacts/workspace-verification.png`.

The app was restarted with the final backend and left running on http://127.0.0.1:5000. The project-local PostgreSQL cluster is running on 127.0.0.1:55432. Existing `.local/login.txt` credentials remain unchanged.

## Scope and remaining limits

The app lists **16 capabilities/limitations: 8 Implemented and 8 Partially Implemented**. The four new entries correspond to the supplied research gaps; their implemented status describes the documented local-platform scope.

- Partitioning is an executed, verified temporary-copy experiment. There is no automatic live-table conversion, foreign-key migration or production cutover.
- Archives preserve order-header snapshots. They omit related line/payment details and reclaim no live storage.
- Mixed ERP updates run on isolated copies and roll back. Commit latency, durable write throughput and production concurrency capacity are unmeasured. Normal/injected-failure cleanup is tested; hard process/server termination can leave a sandbox requiring owner cleanup.
- Query rewriting is limited to the built-in timestamp-without-time-zone date predicate. Arbitrary semantic rewrites are unavailable.
- Timings use warm caches and a shared machine; scheduling and other activity can vary. Negative gains and copied existing indexes remain visible.
- Cumulative PostgreSQL activity counters are not sampled traffic rates. Recommendations remain explainable heuristics.
- No multi-million-row workload, cold-cache/cross-machine study, predictive/ML evaluation, production authentication/deployment hardening or independent penetration test is claimed.

The existing synthetic dataset and live ERP relationships remain valid. No external account or production database was involved.
