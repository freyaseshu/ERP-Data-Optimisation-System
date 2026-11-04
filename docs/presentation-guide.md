# Presentation and live demonstration

Use a 20–25 minute session. Start with the problem, make **Dashboard the first feature**, build toward evidence, and make **Performance Reports the last functional feature**. Discuss limitations before the final evidence/export so the closing demonstration remains a measurable result.

## Rehearse before the audience arrives

1. Open the outer project directory and run `./serve.ps1`. Open **http://127.0.0.1:8080** and check `/health/ready` returns ready. If an app already occupies port 8080, use that instance or stop its own terminal before relaunching.
2. Locate the existing `.local/login.txt` privately. Sign in immediately before presenting; sessions last thirty minutes. Never project the password file, `.env`, a connection string or a terminal containing credentials.
3. Confirm the dashboard has 77,220 ERP records and 18 mapped tables in the prepared medium dataset. Counts can differ on another profile; explain actual values rather than memorized numbers.
4. Choose a reporting day represented by the data: **2025-01-01** works in the prepared dataset. Use an archive cutoff such as **2025-01-01**. Existing snapshots may make the preview zero; this demonstrates repeatability.
5. Rehearse one Workspace assessment using four workers, one writer, eight operations per worker, three timing repeats and seed 42. Know where its saved history and evidence are. A prior run is a fallback if a live experiment is slow.
6. Inspect existing indexes. Previously approved indexes stay installed; repeated demonstrations may say “already present” or produce no new candidate. Do not drop useful indexes just to create an impressive graph. If a new-index comparison is essential, prepare a separate fresh demonstration database beforehand; the loader preserves nonempty databases.
7. Have `docs/verification.md`, the XML test result, a prior JSON export and this guide available. Keep mutation examples on synthetic/demo data. Do not demonstrate duplicate deletion or index changes against production records.

## Suggested opening: 45 seconds

“ERP databases handle frequent order and stock updates while also serving financial and inventory reports. Tuning one query can add indexes that make writes more expensive. Our system connects diagnosis, explainable recommendations, administrator approval and controlled verification. The contribution is an integrated workflow with evidence, rather than an automatic promise that every change will make every workload faster.”

Then briefly name the four gaps: fragmented techniques, limited ERP awareness, opaque/risky recommendations, and missing before-and-after validation.

## Ordered demonstration and talk track

| Step / time | What to do | What to explain | Expected evidence |
|---|---|---|---|
| 1. Dashboard / 1 min | Show live connection, counts, timestamp and measured charts. | “These values come from PostgreSQL and persisted measurements. The charts are not hardcoded claims.” | Actual database status, ERP counts, measurement history. |
| 2. Explorer / 2 min | Open orders, order_items, inventory, payments and transactions. Show a key/relationship, an index and a paginated search/sort. | “The dataset is relational. An order connects to items and payments; a performance change must preserve those relationships.” | Schema, PK/FK metadata, index size and server-side browsing. |
| 3. Analyser / 2 min | Run the SQL below in estimated mode, then EXPLAIN ANALYZE; preview results. | “Planner cost is an estimate in planner units. Actual execution is measured in milliseconds. The preview is capped at 100 rows.” | Estimated vs actual rows/time and visible plan. |
| 4. Query Optimiser / 1–2 min | Analyze the same query; review any candidate, its SQL and trade-offs. If no candidate appears, show existing indexes and saved recommendations. | “Recommendations are heuristics. An existing covering index is a reason to avoid another index. Approval is an administrator action.” | Candidate or correct existing-index behavior; original query retained. |
| 5. Workspace assessment / 2 min | Select Mixed, reporting day 2025-01-01; assess and expand saved controls/plan evidence. | “This page is the integrated administrative workflow. The five techniques share one assessment and evidence trail.” | Saved configuration, four ERP diagnostics, environment and five Pending actions. |
| 6. Index approval / 1–2 min | Review customer-order index SQL, scope and risk; approve on demo data, or inspect a prior verified action. | “The index, evidence and successful status commit together. Failed verification rolls back changes. Already-present indexes are labelled.” | Samples/plans, equivalent results, storage data or existing-index note. |
| 7. Query rewrite / 1 min | Approve the built-in date rewrite. Expand result evidence. | “Casting the timestamp column to date is compared with a half-open timestamp range. We check the same output, and do not automatically replace application SQL.” | Before/after samples and full result equivalence. |
| 8. Partition experiment / 2 min | Review the generated monthly partition SQL and approve. Show full-copy equality and partitions scanned. | “We physically test monthly partitions on temporary copies with equal indexes. The report can prune unrelated months. We do not convert live tables or migrate their foreign keys.” | Complete-copy equality, partition count, scanned names and plans. |
| 9. ERP concurrency / 2 min | Run the mixed-workload comparison. Show per-operation means/p95 and throughput. | “Order and stock updates run alongside lookups and reports. Both phases replay the same seeded operations. Updates roll back on isolated copies; this measures local read/write trade-offs, not production capacity or commit latency.” | Financial/inventory/lookup/update samples, matching read results, unchanged copies and sandbox cleanup. |
| 10. Archive and duplicates / 2 min | Show Workspace archive preview/verified snapshots or standalone Archive; scan duplicate groups. Demonstrate rejection/review rather than deleting records for spectacle. | “Archives save header snapshots and preserve live relationships. Duplicate groups require human interpretation; referenced records cannot be deleted.” | Snapshot count/history, repeatability, duplicate review or honest empty state. |
| 11. Benchmarks / 1–2 min | Expand one workload's SQL/index and a stored result; run a single comparison if time permits. | “Seven workloads cover joins, aggregation, sorting, inventory and ledger lookup. Equal warm-ups, repeated timings and same-snapshot checks make the comparison reviewable.” | Real samples/plans, variation, equivalence and existing-index labels. |
| 12. Safety and limitations / 2 min | Briefly show Limitations and optionally an Analyst session in a separate browser. | “Analysts can inspect and assess, but cannot approve mutations. The four gaps are addressed at local-platform scale. Live partition cutover, complete lifecycle archiving, MFA and production-scale studies remain outside the implementation.” | Visible limitation solutions/remaining work and disabled administrative controls. |
| 13. Reports — final feature / 2 min | Filter a useful date range, show trends and before/after results, export CSV and the Workspace JSON. | “The final output is reproducible evidence: configuration, SQL/plans, samples, decisions and verified results. Positive, neutral and negative results all remain available.” | Downloadable CSV/JSON and linked run/action IDs. |

## SQL to use for the analyser

```sql
SELECT id, customer_id, order_date, status, total_amount
FROM orders
WHERE customer_id = 101
ORDER BY id;
```

If it already uses an index, explain the access path rather than claiming a missing index. For a broader financial query:

```sql
SELECT status, COUNT(*) AS orders, SUM(total_amount) AS revenue
FROM orders
GROUP BY status;
```

For the workspace rewrite discussion:

```sql
-- Baseline
SELECT id, customer_id, order_date, total_amount, status
FROM orders
WHERE order_date::date = DATE '2025-01-01'
ORDER BY id;

-- Verified alternative: run individually in the analyser, not as stacked SQL
SELECT id, customer_id, order_date, total_amount, status
FROM orders
WHERE order_date >= TIMESTAMP '2025-01-01'
  AND order_date < TIMESTAMP '2025-01-02'
ORDER BY id;
```

The analyser intentionally accepts one statement at a time. The workspace already creates and compares these alternatives safely.

## How to interpret the results aloud

- “Before and after are actual PostgreSQL server execution times. Result hashing is checked separately.”
- “The percentage is `(before - after) / before * 100`. Positive means lower measured read time; negative means a regression.”
- “A high percentage on a sub-millisecond query is a small absolute difference. Timing variation and write overhead matter.”
- “A sequential scan can be the correct plan for a small table or a broad filter. It is not automatically a fault.”
- “Identical results mean the full row multisets match, including duplicates; the standard comparison ignores row ordering.”
- “An existing-index rerun is repeat measurement, not proof of a new optimization.”
- “p95 is a latency percentile within this small experiment. Eight workers and a few operations are a functionality experiment, not a capacity certification.”

## Questions you are likely to receive

**Is this a complete ERP product?** No. It is an ERP database optimization, inspection and verification platform using related synthetic ERP data.

**Does it optimize automatically?** It diagnoses and proposes candidates. Administrators approve live mutations; general automatic query rewriting is unavailable.

**What is your main contribution?** The integration of ERP-aware assessment, several optimization techniques, explainable approval and retained before/after evidence.

**How do you protect the data?** Read-only query validation/transactions, a restricted reader in production, current database role checks, CSRF protection, throttled login, bounded sessions, explicit approvals and rollback on failed verification. Backups and restore rehearsals are separate operational protections.

**Does archiving reduce the live database size?** No. It saves order-header snapshots without deleting source rows; it is not a space-reclaiming archive.

**Are live orders partitioned?** No. The feature runs real partition experiments on temporary copies. Live conversion requires a separate key/reference migration and cutover plan.

**Can you promise faster production performance?** No. The tool retains measurements, regressions and verification evidence on synthetic local data. Production workload, hardware, concurrency and commit durability need separate validation.

**Is it deployment-ready?** The Windows Waitress path, security controls, restricted-role rehearsal, readiness checks and backup restore are validated locally. A hosted server still needs your real TLS/DNS, restricted OS/database accounts, current patches, managed startup, monitoring and site-specific acceptance. Do not call the development Flask server a production deployment.

## Closing: 30 seconds

“We started with an ERP workload, inspected the plan, reviewed a tuning action, required administrator approval and verified the result. The final report records the evidence, including cases where a change is neutral or slower. The four research gaps are addressed within the demonstrated local platform, and the remaining production limitations are documented.”

For a ten-minute presentation, keep Dashboard, Explorer, Analyser, one Workspace date/partition result, one mixed-workload result, a brief limitations explanation and the final Reports export. Show stored evidence for slower actions. If PostgreSQL or a benchmark is unavailable, state the failure, show the saved result and controls, and avoid inventing a successful measurement.
