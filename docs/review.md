# Code review and repair record

The received folder was not a Git checkout, so no commit/PR diff was available. Work was performed directly in the existing inner application folder. No existing external database or Windows database service was detected. A new project-local PostgreSQL cluster was created for real verification.

| Finding | Repair |
|---|---|
| Two independent SQLAlchemy instances split model metadata | One shared instance in utils/db.py; legacy imports point to it |
| Missing model imports/incorrect PerformanceLog class name | Complete model registry and compatibility alias |
| Active dependencies and schema incompatible with PostgreSQL additions | psycopg 3, consistent PostgreSQL model/schema generation and connection validation |
| Most feature blueprints commented out | Registered all existing feature routes and repaired navigation |
| Product/order/inventory fields differed between loader, models and queries | Unified fields, relationships and legacy ORM aliases |
| Seed-account password bypass | Removed; Werkzeug hash verification for every account |
| Optimiser executed arbitrary SQL before validating it | AST validation before execution; read-only connection, table/function/cast restrictions and timeouts |
| Index DDL accepted by prefix only, without role checks | Database-backed Admin check, stored recommendations, constrained grammar and catalog validation |
| PostgreSQL EXPLAIN interpreted with another database's columns | PostgreSQL JSON plan traversal and separate estimated/actual views |
| Benchmark called nonexistent methods and silently swallowed index/log errors | Working repeated measurements, stable snapshot, full equivalence check and atomic DDL/evidence |
| Dashboard hardcoded example timings | Actual counters, stored evidence, timestamps and empty/error states |
| Explorer exposed users/password hashes and unsafe HTML | ERP-only browsing, validated sort/pagination, escaped values and metadata |
| Duplicate deletion could accept unrelated IDs and cascade | Verify group membership and reject referenced records |
| Archive deleted orders and related ERP data | Idempotent non-destructive order snapshots and history |
| Generated data had partial commits and could reset account passwords | Atomic loader, exact counts, no destructive regenerate flag, account preservation |
| Scripts continued after failed commands | Root-relative PowerShell helpers with checked exit codes |
| Unsubstantiated limitation/test claims | Code-based capability descriptions, partial statuses and links to actual verification |
| README merge markers and obsolete setup | Replaced with executable PostgreSQL instructions and academic documentation |
| CDN-only frontend assets | Vendored existing UI dependencies for offline presentation |
| Tests targeted nonexistent routes or a different driver | Real PostgreSQL integration tests in disposable databases |

The supplied historical result CSVs remain as unverified legacy files and are not displayed by the application. The old scratch password-guessing script was retired; a configured-credential PostgreSQL connectivity diagnostic replaces it. Check `verification.md` for what was actually executed; this review is not a claim of production readiness.
