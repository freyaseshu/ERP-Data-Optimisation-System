# What this codebase does

This is an **ERP database optimization and evidence platform**. It helps an administrator inspect related ERP data, diagnose slow queries, review tuning proposals, approve controlled changes and verify their effects. It is not a complete ERP transaction-entry system: it does not provide an order-entry UI, payroll processing, general-ledger accounting or a production ERP integration.

The stack is Flask, SQLAlchemy/Flask-SQLAlchemy, psycopg 3 and PostgreSQL. Server-rendered Jinja pages use local Bootstrap, JavaScript and Chart.js assets; presentation pages do not need internet access. Waitress provides the Windows-compatible deployment server. There is no separate frontend build/server.

## Data model

Ten related ERP tables represent departments, employees, customers, suppliers, products, orders, order items, inventory, payments and transactions. Relationships include customers/employees to orders, orders to items/payments, products to items/inventory, suppliers to products and payments to ledger transactions. PostgreSQL keys and checks enforce basic consistency.

The medium synthetic profile has **77,220 records**: 20 departments, 250 employees, 4,500 customers, 250 suppliers, 1,200 products, 14,000 orders, 30,000 order items, 3,000 inventory positions, 12,000 payments and 12,000 transactions. Small and large profiles contain 11,730 and 142,635 ERP records; scaling is available. A seeded generator uses decimal amounts, matching order/item totals, matching payments and reserved synthetic email domains. It preserves nonempty databases and rolls back a failed load.

Eight support tables store users, recommendations, performance logs, order-header snapshots, archive logs, a compatibility limitation model, optimization assessments and login throttles. The current mapped schema has **18 tables**. The displayed limitation catalogue comes from implementation-backed service definitions, not old database claims.

## Login and permissions

Accounts use Werkzeug password hashes. Administrators can approve indexes, execute benchmarks, archive headers, delete eligible duplicates and approve/reject workspace actions. Analysts can browse, analyze, assess and inspect/export evidence, but cannot approve those administrative mutations. Requests check the current database user/role; stale account sessions are revoked.

New deployment protections include PostgreSQL-backed account/IP login limits, CSRF tokens for forms and JSON requests, POST-only logout, signed thirty-minute sessions, no-store responses, security headers and CSP script nonces. Production mode requires a configured random secret, an HTTPS public hostname, secure cookies and a separate restricted reader. MFA and SSO are not implemented. See the [deployment guide](deployment.md) for operator requirements.

## Dashboard

Shows actual connection/version information, ERP record/table/index counts, slow-query counts, recommendation states and recent measured queries. Charts are built from persisted measurements, not invented percentages. Refresh is manual or optionally every thirty seconds. This is sampled application history, not a continuous database activity collector.

## Database Explorer

Lets users inspect ERP table counts, columns, primary/foreign keys, index definitions, sizes and scan counters. Browsing supports server-side pagination, search and sorting with bound values and allowlisted identifiers. It exposes the ERP tables rather than user/password/support tables. Large-table counts and broad searches can still be expensive.

## Database Analyser

Accepts one validated PostgreSQL SELECT, including approved read-only CTEs. Estimated EXPLAIN shows planner costs/rows without executing the query; EXPLAIN ANALYZE executes it and records actual timing/rows/buffer evidence. The page distinguishes planner cost units from elapsed milliseconds. Filtered sequential scans and disk sorts can produce explanatory warnings. Result preview returns at most 100 rows.

AST checks reject modifying SQL, stacked statements, data-modifying CTEs, SELECT INTO, row locks, non-ERP relations, unsafe functions/casts, custom/qualified operators and unsupported table-sampling methods. Transactions impose read-only mode, controlled search path and timeouts. Production checks require an independently restricted ERP reader. This is an allowlisted analysis interface rather than an unrestricted SQL console.

## Query Optimiser

Uses actual plans to find filtered sequential-scan index candidates. It checks catalog columns, primary keys and existing index prefixes. It also gives manual projection advice for SELECT *. Recommendations retain the original query, proposed index SQL, explanation and status. An Admin reviews/approves or rejects them.

Approved application compares the original query before/after, retains complete results and plans, and commits the index, evidence and Applied status together. A failure rolls those effects back; a failed status is retained separately. Already covered queries may legitimately produce no new candidate. This is heuristic tuning, not machine learning or a general cost-based advisor.

## Optimization Workspace

Connects assessment, review, approval, execution, verification and export in one persisted workflow. Choose mixed, transactional, financial or inventory focus, reporting day, archive cutoff, timing iterations, workers/writers, operation count and seed. Assessment records actual ERP plans, counts, current indexes, environment and cumulative database counters.

Each assessment presents five actions:

| Action | Actual behavior | Important boundary |
|---|---|---|
| Customer-order index | Skip an existing covering leading-column index or create the approved index, compare the same query and verify results. | Storage/write cost can outweigh read gains; controlled comparisons briefly block writes. |
| Date-predicate rewrite | Compare a built-in timestamp-to-date filter with an equivalent half-open timestamp range. | Applies only to the known timestamp-without-time-zone schema/query; application SQL is not automatically replaced. |
| Monthly partition experiment | Create temporary heap and monthly range-partitioned copies, add equal date indexes, ANALYZE, verify every copied row and compare date-report plans/times. | All copies disappear; live table keys, references and storage are not migrated. A default partition preserves null dates; at most 120 observed months are accepted. |
| Historical order snapshots | Copy eligible unsnapshotted order headers, verify the new values and verify all live orders remain unchanged. | Excludes item/payment detail and does not delete live rows or reclaim space. Old snapshots remain point-in-time records. |
| Mixed ERP comparison | Copy orders/inventory into an isolated schema; replay identical seeded reads/reports/updates with 2–8 workers before/after candidate indexes; compare every read result and final copied data. | Every UPDATE rolls back; commit latency and durable throughput are excluded. Scheduling is not deterministic. Normal success and tested failures remove the sandbox; abrupt process/server termination can leave a schema needing owner cleanup. |

Action cards show SQL, rationale, risks and scope. Admin approval is explicit and per action. Rejections, failures, retries, actor names and UTC decisions persist. Verified/applied/rejected actions cannot execute again in the same assessment. Full JSON exports preserve configuration, diagnostics, decisions, timings and result evidence. Measurements also link into Reports.

The mixed experiment measures per-operation count, mean, p50, p95, standard deviation and raw samples, plus overall throughput. Per-operation latency excludes connection checkout and result hashing; overall throughput includes worker startup and hashing. Existing indexes are copied to both phases; second-phase candidates can be redundant, and this is disclosed. Results can get worse after indexing.

## Benchmarks

Seven fixed ERP workloads cover customer-city lookup, delivered customer/order joins, category/price sorting, revenue grouping, supplier sales, stock replenishment and payment/ledger lookup. An Admin can approve one or the suite. Only the shown index definitions can execute.

Each comparison uses a stable repeatable-read snapshot and locks against concurrent ERP writes, equal excluded warm-ups, repeated EXPLAIN ANALYZE samples, mean/variation and complete row-multiset equivalence. SHA-256 multisets preserve duplicate counts while ignoring row order. Existing indexes are retained and labelled. The index and measurement log commit together; failures roll back. Negative improvements remain visible. Warm caches and background machine activity influence results.

## Duplicate Checker

Finds potentially matching groups using configured business fields: customer email; product name/category/price; inventory product/location; and order customer/date/amount. It returns at most 200 groups. An Admin can explicitly retain one record and delete selected matching, unreferenced records. Foreign-key references block deletion so related ERP data is protected. Matching fields do not prove that records are semantically interchangeable; human review remains necessary.

## Data Archive

Previews old orders without header snapshots and saves missing snapshots after Admin confirmation. It records time, actor and count, and repeated execution does not duplicate headers. Live orders/items/payments/transactions remain present. This is a non-destructive snapshot feature, not a complete lifecycle archive or a backup/recovery system. The separate backup script handles complete database dumps.

## Performance Reports

Filters persisted measurements by today, seven/thirty days, all or an inclusive custom date range. Shows timing summaries, slowest/fastest queries, trends and CSV evidence. Workspace results carry run/action IDs. Timing summaries/CSV are bounded to the most recent 1,000 selected measurements; the UI discloses truncation and recommends narrower dates. Duplicate/index/archive totals describe the current system rather than the selected measurement period.

Percent improvement is `(before - after) / before * 100` for a positive baseline; otherwise it is unavailable. A positive percentage means lower measured read time, a negative value is a regression. An existing-index rerun must not be presented as a newly applied optimization.

## Limitations and deployment operations

The Limitations page lists 16 implementation-backed entries, currently eight Implemented and eight Partially Implemented. It includes the four supplied research gaps plus scale, automation, database dependency, environment, indexing overhead, monitoring, security, realism, benchmark reliability, concurrency and prediction. Each entry has its solution and remaining work. Implemented means the documented local scope exists, not that all production research problems are solved.

Operations include an additive schema initializer, synthetic dataset loader/validator, account creation, reader provisioning, Waitress launchers, production preflight, minimal health endpoints and private database backup with optional disposable restore verification. No machine service, firewall, domain or TLS configuration is changed automatically.

## The four supplied research gaps

| Gap | How the application addresses it | Remaining boundary |
|---|---|---|
| Fragmented optimization | One Workspace joins query, index, partition, archive and verification steps with saved decisions/evidence. | Live partition migration and destructive space-reclaiming retention are not implemented. |
| Lack of ERP awareness | ERP-specific financial/inventory/order workloads and concurrent read/UPDATE profiles measure read gains alongside write cost. | Synthetic local workloads; no production concurrency or commit-latency claim. |
| Missing explainable, safe recommendations | Actual plans, visible SQL/trade-offs, current Admin role checks, explicit approval and rollback on verification failure. | Fixed/heuristic candidates; no learned advisor, MFA or independent security certification. |
| Missing before/after analytics | Repeated timings, variation, full result checks, same-snapshot/equal-copy controls, history and JSON/CSV evidence. | Warm-cache shared-machine measurements; no hardware-isolated/cold-cache or universal performance guarantee. |

See [research-gaps.md](research-gaps.md) for implementation mapping, [verification.md](verification.md) for executed checks, and [presentation-guide.md](presentation-guide.md) for a spoken demonstration sequence.
