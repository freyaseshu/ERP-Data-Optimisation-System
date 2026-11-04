# Executed verification — 21 October 2026

Local environment: Python 3.12.10; PostgreSQL 17.11; Windows reported as Windows 10 by Python; AMD64; 12 logical CPUs. PostgreSQL is project-local on 127.0.0.1:55432. Website: http://127.0.0.1:5000.

## Automated tests

**115 passed; 0 failed; 0 errors; 0 skipped** in 33.720 seconds. Executed through the outer `.\test.ps1` forwarding command. Machine-readable result: `artifacts/test-results.xml`.

Tests used disposable real PostgreSQL databases. All were removed after execution; the demo database was preserved. Tests generated and validated small (11,730), medium (77,220) and large (142,635) profiles, tested injected failure rollback, and verified keys, relationships and monetary totals.

Coverage includes all nine pages, read APIs, capped SQL preview, estimated/actual plans, unsafe SQL/CTE/function/cast rejection, password-bypass rejection, analyst restrictions, read-only enforcement, a real timeout/recovery, recommendations, seven benchmark queries, duplicate-sensitive result equivalence, failed-comparison rollback, partial-index metadata, existing-index reruns, date-filtered CSV, limitation statuses, archive integrity and referenced-record deletion protection.

The controlled concurrent-read check used four workers making five paginated requests each: all 20 returned HTTP 200. This is not a stress test or a production concurrency capacity claim.

## Additional executed checks

- `setup.ps1` rerun: exit 0; existing database/users/data preserved; counts still 77,220. The final rerun was executed in a normal Windows process context; an earlier restricted-shell pg_ctl process check was replaced by an authenticated server/data-directory check.
- Outer `run.ps1`: started Flask successfully on 127.0.0.1:5000 with debug disabled; left running.
- Outer `benchmark.ps1 -ApproveIndexes -Iterations 2`: exit 0; all seven comparisons succeeded with equivalent results. Existing indexes were correctly labelled and negative changes retained.
- `pip check`: no broken requirements. Python compilation and syntax checks on all application JavaScript plus rendered inline explorer/benchmark scripts passed.
- Main and separate reader connections verified. The reader can SELECT ERP data, cannot SELECT password hashes, cannot write, and has no superuser/create-database/create-role privileges.
- Dataset validation: all ten tables populated, PK/FK checks passed, no orphan references, order totals equal item totals, line totals equal quantity/price/discount arithmetic, payment amounts match orders.
- Browser checks: login; live dashboard; actual analyser plans and 100-row capped preview; explorer/search/index sizes; optimiser approval modal and applied audit state; existing-index feedback; reports/trend chart; duplicate empty state; archive preview; benchmark history; limitation filters. No frontend console errors were observed on the checked pages. Archive/delete mutations were tested in disposable databases, not on the demo ERP records.
- Frontend CSS, scripts, chart library and icon fonts are local files; license files are included.

## Actual new-index comparisons

The table lists runs that actually created an index, rather than subsequent warmed reruns. Timings are mean PostgreSQL EXPLAIN ANALYZE execution times in milliseconds; three measured runs follow one warm-up per side. Results matched by complete row-hash multiset including duplicate multiplicity. Full plans, samples, standard deviations and configuration are retained in the database and `artifacts/recorded-benchmarks.json`.

| Query | Before ms | After ms | Change % | Equivalent |
|---|---:|---:|---:|---|
| Customer City Filter & Retrieval | 0.417000 | 0.134667 | 67.71 | Yes |
| Delivered Orders Customer Join | 5.446000 | 0.229000 | 95.80 | Yes |
| Product Category Search & Price Sort | 0.241333 | 0.054333 | 77.49 | Yes |
| Multi-Tier Supply Chain Sales by Supplier | 27.883000 | 23.910333 | 14.25 | Yes |
| Low Stock Reorder Inventory Alert | 0.680667 | 0.388667 | 42.90 | Yes |
| Payment Transaction Ledger Lookup | 0.782667 | 0.048000 | 93.87 | Yes |
| Index orders.customer_id | 0.678667 | 0.017000 | 97.50 | Yes |

The revenue aggregate did not receive a new index because a leading-column index already existed. Reruns include real regressions, for example product sorting 0.0605 → 0.067 ms (−10.74%) with an existing index. Such tiny timing changes are measurement variation, not evidence of a newly applied optimisation. Large relative gains on sub-millisecond queries should not be presented as production guarantees.

## Current demo data

| Table | Records |
|---|---:|
| departments | 20 |
| employees | 250 |
| customers | 4,500 |
| suppliers | 250 |
| products | 1,200 |
| orders | 14,000 |
| order_items | 30,000 |
| inventory | 3,000 |
| payments | 12,000 |
| transactions | 12,000 |
| **Total** | **77,220** |

## Implemented and remaining scope

All 12 limitations have implementation descriptions and remaining work. Current statuses: **4 Implemented, 8 Partially Implemented, 0 Planned, 0 Blocked**. Statuses are conservative capability statements, not a claim that every original master-prompt ambition is complete.

Not run/implemented: multi-million-row tests, sustained production load, cross-machine/cold-cache experiments, index write-overhead benchmarking, predictive/ML evaluation, comprehensive background monitoring, automatic semantic query rewriting, production authentication/deployment hardening and independent penetration testing. Existing incompatible schemas require a reviewed migration. Query equivalence intentionally ignores ordering. Archive retains snapshots and does not reclaim live storage.

No external account, production database or database service was altered. Review methodology and commands are in README, project.md and review.md.
