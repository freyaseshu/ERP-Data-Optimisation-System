# ERP Data Optimisation System

A local Flask application for learning PostgreSQL query tuning on related synthetic ERP data. It includes a database explorer, safe SQL analyser, index recommendations, repeatable benchmarks, reports, duplicate review and order snapshot archives. The original Bootstrap sidebar/card UI is retained.

## Run this repaired copy

The application is in the inner `ERP-Data-Optimisation-System-main` directory. The outer directory also has forwarding PowerShell commands.

```powershell
# From the folder opened in Codex:
.\run.ps1
```

Open **http://127.0.0.1:5000**. A local PostgreSQL 17.11 cluster has been configured on **127.0.0.1:55432** with database `erp_optimisation_db`. It contains **77,220 ERP records**. The application does not need a separate frontend server or internet access to load its CSS, scripts, fonts and charts.

Login credentials for this prepared copy are in the inner folder's **`.local/login.txt`**. Credentials are generated locally; there is no universal password or login bypass. Keep `.env` and `.local` private. Do not copy the prepared virtual environment between machines.

If Flask is already running, just open the URL. Stop its terminal with Ctrl+C before launching a second copy on the same port.

## What was wrong and what changed

The supplied project mixed incompatible database versions: the active dependencies/schema/analyser used a different SQL dialect, while PostgreSQL services were disconnected. Two SQLAlchemy instances owned different models. Most feature routes were unregistered, model imports were broken, benchmarks called absent methods, dashboard charts were hardcoded, and the login had a password bypass. Scripts could report success after failures and the README contained unresolved merge markers.

The repaired app uses **PostgreSQL + psycopg 3 exclusively**, a single model registry, all feature routes, hashed authentication, actual measurements and explicit error/empty states. Benchmarks cannot accept arbitrary DDL. Existing data is preserved during setup/generation. Archive now copies snapshots; it does not delete live orders or cascade away order items, payments or ledger entries.

## Setup on another Windows machine

Requires Python 3.10+ and a supported PostgreSQL server. Python 3.12 and PostgreSQL 17.11 were used for verification.

```powershell
python --version
Get-Service *postgres* -ErrorAction SilentlyContinue
Get-Command psql -ErrorAction SilentlyContinue
# If the tools are not on PATH, locate the installed executable:
Get-ChildItem 'C:\Program Files\PostgreSQL\*\bin\psql.exe' -ErrorAction SilentlyContinue
# Example only: replace 17 with your installed major version.
& 'C:\Program Files\PostgreSQL\17\bin\psql.exe' --version
```

Install PostgreSQL from the [official Windows download page](https://www.postgresql.org/download/windows/) if needed. Installation and starting a Windows service may require an administrator PowerShell. For a configured service, `Start-Service postgresql-x64-17` is an example; use its actual name from `Get-Service`.

Enter the inner application folder before the following commands:

```powershell
cd .\ERP-Data-Optimisation-System-main
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env: set DATABASE_URL and a long random SECRET_KEY.
notepad .env
```

`DATABASE_URL` must use SQLAlchemy's psycopg dialect:

```dotenv
DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/erp_optimisation_db
SECRET_KEY=your-own-long-random-secret
QUERY_TIMEOUT_MS=5000
SLOW_QUERY_MS=100
```

URL-encode special characters in the username/password. The example credentials are placeholders. The configured account needs database creation permission for `--create-database`. Otherwise have the database owner create `erp_optimisation_db`, grant the required schema/table privileges and initialise without that flag.

```powershell
.\venv\Scripts\python.exe scripts\init_db.py --create-database
.\venv\Scripts\python.exe scripts\generate_dataset.py --size medium
.\venv\Scripts\python.exe scripts\validate_dataset.py
.\venv\Scripts\python.exe scripts\create_user.py --username admin --role Admin
# Optional separate ordinary analyst account:
.\venv\Scripts\python.exe scripts\create_user.py --username analyst --role Analyst
# Recommended: run as the database owner to create a restricted SQL reader:
.\venv\Scripts\python.exe scripts\configure_readonly.py
.\run.ps1
```

The user script prompts for a password of at least ten characters. Alternatively supply `ERP_ADMIN_PASSWORD` for a controlled local setup; do not put it in source code. Existing accounts and passwords are preserved. Restart Flask after configuration changes.

After `.env` is configured, **`.\setup.ps1`** installs dependencies, creates the database/schema if needed, loads only an empty ERP database and validates it. It exits on failure. It never silently removes data. If PowerShell blocks local scripts, invoke individual Python commands above, or use a process-scoped execution policy suitable for your environment.

## Optional project-local PostgreSQL

This prepared copy has EDB's official Windows binaries in `.local/pgsql` and its cluster in `.local/pgdata`. No PostgreSQL Windows service was installed or changed. These local resources are ignored by version control.

```powershell
.\venv\Scripts\python.exe scripts\local_postgres.py status
.\venv\Scripts\python.exe scripts\local_postgres.py start
.\venv\Scripts\python.exe scripts\local_postgres.py stop
```

`run.ps1` starts this cluster when present. On a fresh machine, either use installed PostgreSQL or extract the [official EDB binaries](https://www.enterprisedb.com/download-postgresql-binaries) to `.local/pgsql`, then run `scripts/local_postgres.py init` **before creating `.env`**. Initialisation refuses to overwrite an existing configuration or cluster. It creates a random database password and an admin login file. Run `scripts/configure_readonly.py` afterward to create the separate restricted reader.

## Data and schema

The ten ERP tables are related through primary and foreign keys. Monetary amounts use decimal arithmetic. Every order has items and a total matching those items. Payments match their orders. Transactions reference payments. Emails use the reserved `example.invalid` domain. Inventory positions are unique in the generated data.

| Table | Medium / prepared copy |
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
| **Total ERP records** | **77,220** |

Six supporting tables hold users, recommendations, measurements, snapshot archives, archive logs and a compatibility limitations model. The 12 displayed limitation entries are defined by the implementation in `services/limitations_service.py`; stale seeded database claims are not used.

```powershell
.\venv\Scripts\python.exe scripts\generate_dataset.py --size small
.\venv\Scripts\python.exe scripts\generate_dataset.py --size large --scale 1 --seed 42
```

Profiles contain **11,730 / 77,220 / 142,635** ERP rows. `--scale` accepts 1–100 and multiplies each count. **For another profile, configure a new empty database.** A nonempty database is left intact and its actual counts are printed. No destructive regeneration flag is provided. The loader holds a transaction across all inserts; any failure rolls back the entire dataset. `database/schema.sql` is PostgreSQL DDL generated from the same model metadata. The generator is the primary loader; no duplicate bulk SQL dataset is maintained.

`init_db.py` adds missing tables/check constraints. It is not a general migration tool: an incompatible existing table causes a clear failure before data is rewritten. Review and back up an older schema before writing a migration.

## Demonstration

1. Open Dashboard and show actual connection, counts and refresh timestamp. Charts show recorded measurements only.
2. Open Database Explorer; inspect orders, order items, products, inventory, payments and transactions. Show PK/FK relationships, index definitions/sizes and pagination. Enter a search term and press Enter.
3. Open Database Analyser and select an ERP query. Compare the estimated plan with **Measure with EXPLAIN ANALYZE**. Estimated costs are planner units; actual times are milliseconds. The preview button executes a validated read-only query and returns at most 100 rows.
4. Open Query Optimiser. Start with `SELECT * FROM orders WHERE customer_id = 101;`. Review the candidate and its storage/write trade-off. An Admin can approve and benchmark or reject it. The original query is retained. If an appropriate index already exists, no new recommendation is needed.
5. Open Benchmarks and expand a workload's SQL/index. Approve a single index or the suite. The workloads cover customer filters, customer/order joins, product sorting, revenue aggregation, supply-chain sales, stock alerts and payment/ledger tracing.
6. Show full result-equivalence status, timing variation and stored plans in benchmark history. New indexes remain installed. Reruns explicitly say when an index already exists and do not attribute timing variation to a newly applied change.
7. Open Performance Reports, select a date range, view recorded timing trends and download CSV evidence.
8. Open System Limitations and filter by actual implementation status. Explain what is partial or unavailable.
9. Show `docs/verification.md` and the executed automated test report.

## Tests and benchmarks

```powershell
.\test.ps1
# Or:
.\venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --junitxml=artifacts/test-results.xml
# Review services/benchmark_service.py before approving its known indexes:
.\benchmark.ps1 -ApproveIndexes -Iterations 3
```

Tests create disposable databases with generated `erp_test_` names and remove only those databases. The configured owner must have `CREATEDB`; tests do not delete or replace demo data. They cover real connectivity/schema/constraints, all dataset sizes, generator rollback/reruns, pages/APIs, pagination/search/sort, SQL safety, role permissions, timeouts, recommendation application, benchmark persistence/equivalence/rollback, CSV, archive integrity and a small concurrent read check. See `docs/verification.md` for the actual result, scope and limits.

Benchmarks use the same repeatable-read snapshot, lock ERP tables against writes, perform an excluded warm-up on both sides, repeat actual `EXPLAIN ANALYZE` measurements and compare SHA-256 row multisets with duplicate multiplicity. Result order is ignored. Full result hashing is separate from the reported server timing. The index and performance log commit together, or both roll back. One index creation at a time is recommended; lock timeout errors are reported rather than hidden.

`((baseline_ms - after_ms) / baseline_ms) * 100` is used when the baseline is positive; otherwise improvement is unavailable. Negative improvements are kept. Files in `artifacts/` include timestamped CSV/JSON evidence. Historical CSVs under `tests/` from the supplied project are unverified legacy artifacts and are not imported or displayed as actual measurements.

## Security and scope

Ordinary SQL is parsed as a PostgreSQL AST, restricted to one SELECT (including read-only CTEs), approved pure functions, built-in casts and ERP relations. System/user/password tables, modifying CTEs, SELECT INTO, row locks, unsafe functions and stacked statements are rejected. A transaction enforces read-only mode, restricted search path and statement/lock timeouts. `configure_readonly.py` provisions a separate account with SELECT on only the ten ERP tables; its URL is private in `.env`. Without it, the same restrictions run through read-only transactions on the main connection.

Index approval, duplicate deletion, archiving and benchmark execution require a database-backed Admin role check. Index DDL comes from a recorded recommendation or the fixed workload and is checked against catalog metadata. The ordinary SQL API cannot execute arbitrary DDL. JSON mutations reject cross-site browser requests; no permissive CORS is enabled. Session cookies use HttpOnly and SameSite=Lax. All values used by explorer/filter tools are bound parameters. Database error handling does not return connection passwords or raw parameter dumps.

This is a local academic application, with a development Flask server. It has no MFA, login-rate limiting, comprehensive activity monitor, evaluated predictive model or production-scale concurrency testing. Benchmark results on synthetic data do not establish production gains. Archive is a non-destructive snapshot, not a space-reclaiming lifecycle system. Duplicate detection shows at most 200 groups and does not prove business records are semantically identical. Referenced records cannot be deleted from this tool.

## Troubleshooting and stopping

- Connection error: check PostgreSQL status, host/port/database and `.env`. This copy uses 55432; a typical installed server uses 5432.
- `psql` not found: use its full installed path, or the Python setup commands; none requires `psql` on PATH.
- Missing tables/columns: run `scripts/init_db.py`; an incompatible existing schema needs a reviewed migration.
- Missing modules: use `venv/Scripts/python.exe`, not an unrelated Python installation; rerun setup.
- Login fails: create a user or consult `.local/login.txt` in the prepared copy. There is no `admin/password` shortcut.
- No charts: charts require real recorded logs; run an analysis/benchmark. Chart assets are local.
- Index already exists: inspect its catalog definition. Benchmarks retain it and label the comparison honestly.
- Lock timeout: finish other write/benchmark operations, then retry. Benchmarks briefly block writes.
- Port 5000 occupied: use the already running app or stop its terminal with Ctrl+C. Do not start a second instance.
- Stop Flask with **Ctrl+C**. Stop the optional local database separately with `scripts/local_postgres.py stop`. If a background Flask process was started for verification, its PID is recorded in `.local/flask.pid`; verify that PID belongs to this app before stopping it.

See `docs/project.md` for academic project documentation and `docs/review.md` for the repair review.

References: [PostgreSQL read-only transactions](https://www.postgresql.org/docs/current/sql-set-transaction.html), [EXPLAIN](https://www.postgresql.org/docs/current/sql-explain.html), [SQLAlchemy PostgreSQL dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html).
