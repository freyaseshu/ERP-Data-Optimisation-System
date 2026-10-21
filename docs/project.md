# ERP Data Optimisation System — project documentation

## Abstract and problem

ERP data spans customers, orders, product catalogues, stock and financial activity. As it grows, a query can spend unnecessary work scanning, joining or sorting rows. This project provides a reproducible synthetic workload and a local website for examining PostgreSQL execution plans and measuring approved index changes. It demonstrates query tuning; it is not a complete operational ERP or predictive optimiser.

## Objectives and scope

Create related synthetic data at configurable sizes; expose metadata and bounded record browsing; safely inspect ordinary SQL; identify candidate indexes and projection improvements; require administrative approval for schema changes; compare actual results and timings; retain evidence and honest limitation status. Preserve the existing Flask/templates/services structure and simple Bootstrap UI.

## Architecture and workflow

Browser HTML/JavaScript → Flask blueprints → services → shared Flask-SQLAlchemy registry → PostgreSQL via psycopg 3. All browser assets are local. Credentials remain in environment configuration. An optional dedicated reader account is used by ordinary SQL analysis; approved administrative operations use the owner connection. Session authentication stores a user identifier and role; administrative endpoints verify the stored user's current database role.

Routes provide dashboard/connection state, explorer metadata/data, estimated/actual SQL analysis, capped execution, recommendations/rejection/application, benchmark execution/history, reports/export, limitations, duplicate review and snapshot archives. Templates share the same sidebar, cards and colours. Read operations are separated from approved index creation and explicit data tools.

## Database and data design

Departments → employees. Suppliers → products. Customers and employees → orders. Orders and products → order items. Products → inventory. Orders → payments. Payments → transactions. The support tables store hashed users, measurement evidence, recommendations, archive snapshots and archive logs. Check constraints reject invalid roles/statuses and negative monetary/stock quantities.

The primary dataset generator uses a fixed seed, synthetic businesses/names, reserved email domains, varied categories/cities/statuses and a fixed two-year date reference. Decimal calculations produce item totals and matching order/payment values. Core inserts occur in one transaction with batching and a validated count for each table. All profiles and scale options are documented in README. A rerun preserves any nonempty ERP database; different scales should use separate empty databases.

The ledger is synthetic payment-linked activity. It is not an audited double-entry accounting model, and no real personal or financial information is intentionally loaded.

## Query optimisation methodology

Parse user SQL using PostgreSQL's grammar before execution. Reject modifying/multi-statement/unsafe queries. Run estimated JSON EXPLAIN or actual JSON EXPLAIN ANALYZE under transaction read-only restrictions and timeouts. Recursively inspect scan/join/sort nodes, estimated rows, actual rows, costs, execution/planning times, filter removal and disk sorts. A sequential scan is not automatically classified as a problem.

Candidate indexes are inferred conservatively from filtered sequential scans and checked against columns, primary keys and existing index prefixes. Suggestions include storage and write overhead. Projection suggestions require human selection; automatic semantic rewriting and cost-based index selection are unavailable. Persist recommendations as Pending, Applied, Rejected or Unsuccessful. Admin approval uses the stored query/DDL rather than arbitrary client SQL.

## Benchmark methodology

Use a stable repeatable-read snapshot and table locks to keep results comparable. For each side, perform a warm-up, run repeated EXPLAIN ANALYZE measurements, retain all execution-time samples, calculate mean/standard deviation, and retain complete plans. Separately stream the query results into a multiset of SHA-256 row hashes, preserving duplicate multiplicity. Compare full multisets; result order is outside this check.

Apply only the approved index. Keep index creation and evidence insertion in one transaction; failures or equivalence mismatch roll both back. Record database settings, OS/architecture/Python/CPU information, dataset row counts and timestamp. Report improvement as ((baseline − after) / baseline) × 100 for a positive baseline, preserving regressions. Reused indexes are explicitly labelled; they are not removed to make a demo look faster. Server times exclude network transfer and result hashing. Shared caches are not flushed and background host activity can influence measurements.

## Testing and actual results

Tests use real, disposable PostgreSQL databases, not a substitute engine. The suite validates schema keys/checks, dataset counts/foreign keys/monetary consistency, safe reruns and failure rollback, all pages/APIs, filtering/sorting/pagination, authentication and roles, read-only enforcement and timeouts, recommendation audit, all benchmark workloads, equivalence mismatch rollback, reports/CSV, limitations, archive preservation and guarded duplicate deletion. Small concurrent reads have a clearly bounded workload.

Actual executed counts, timings and test outcomes are recorded in `verification.md`. Persisted benchmark evidence powers charts and CSV; no legacy example measurements are inserted into the app. Tiny measurements and synthetic data should not be presented as universal production performance gains.

## Limitations and future work

The 12-entry limitations page reflects the shipped implementation and remaining work. Substantial boundaries remain: no evaluated predictive analytics, continuous query collector, production-scale load testing, automatic safe query rewriting, write-cost benchmarking, space-reclaiming archive or production authentication/deployment hardening. Potential work includes measured write overhead, workload-based index prioritisation, pg_stat_statements collection, representative skew distributions and a proper migration/versioning pipeline.

## Installation, execution and demonstration

Use the exact PowerShell commands, PostgreSQL configuration, account creation steps and numbered mentor demonstration in README. The prepared local app runs on 127.0.0.1:5000 with PostgreSQL on 55432. No separate frontend service is required. The test runner and benchmark runner propagate failure codes, and setup preserves existing data.
