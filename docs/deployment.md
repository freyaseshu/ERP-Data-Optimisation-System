# Windows deployment and operations

This release has two intended paths: a local presentation on loopback HTTP, and an administrator-managed Windows server behind HTTPS. The application is an internal database administration tool. Use a dedicated database, trusted users and network access controls. Approved index benchmarks acquire table locks and can block ERP writes; schedule them outside busy periods.

`python scripts/package_release.py` creates a source ZIP with a SHA-256 file manifest. The allowlist excludes private environment files, `.local`, installed environments, caches and generated evidence. Extract it to a new deployment directory, create a fresh virtual environment and configure private settings there. `requirements.txt` uses `constraints.txt` to retain the versions from the verified Windows environment; optional audit tooling is installed only through `requirements-dev.txt`.

## Local presentation: the prepared machine

1. Open PowerShell in the outer project folder already used in this workspace.
2. Run `./serve.ps1`. The forwarding script enters the inner application folder, verifies/starts the existing local PostgreSQL cluster and launches Waitress after read-only startup checks.
3. Open **http://127.0.0.1:8080**. Use the existing credentials in the inner `.local/login.txt`. No password is embedded in the source.
4. Check **http://127.0.0.1:8080/health/ready**: it must return `{"status":"ready"}`. `/health/live` checks only the application process.
5. Stop the app using Ctrl+C in its terminal. Do not launch a second process on the same port. PostgreSQL can remain running, or be stopped separately using `scripts/local_postgres.py stop`.

`run.ps1` still starts the development server on port 5000 for development. Use `serve.ps1` for the presentation. Local presentation mode permits HTTP cookies and the prepared local database owner; those settings are rejected or reported as failures by the production checks where appropriate.

## Fresh Windows machine

Run the following inside the **inner** application directory. Use a maintained Python 3.12 patch release and a maintained PostgreSQL 17 patch release. The executed local tests used Python 3.12.10 and PostgreSQL 17.11; installing current server/runtime security patches is the operator's responsibility.

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade 'pip>=26.2,<27'
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env privately: database URL and a random secret.
.\venv\Scripts\python.exe scripts\init_db.py --create-database
.\venv\Scripts\python.exe scripts\generate_dataset.py --size medium
.\venv\Scripts\python.exe scripts\create_user.py --username admin --role Admin
.\venv\Scripts\python.exe scripts\configure_readonly.py
.\venv\Scripts\python.exe scripts\deployment_check.py
.\serve.ps1
```

Database creation requires an owner/maintenance account with CREATEDB; reader provisioning requires role-creation privileges. Generate synthetic data only in a dedicated empty demonstration database. Existing data is preserved; changing profile does not erase or replace an existing dataset. Never copy the prepared virtual environment between machines.

## Hosted Windows server: provision separate restricted roles

Use a PostgreSQL maintenance account for these one-time operations. This example creates a **new** database and roles. If these names already exist, stop and inspect them; do not overwrite credentials, transfer existing table ownership blindly or reuse the prepared superuser as a production account. The `\password` commands prompt securely; choose distinct strong passwords.

```sql
CREATE ROLE erp_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
\password erp_app
CREATE ROLE erp_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
\password erp_reader
CREATE DATABASE erp_optimisation_prod OWNER erp_app;
REVOKE ALL ON DATABASE erp_optimisation_prod FROM PUBLIC;
GRANT CONNECT ON DATABASE erp_optimisation_prod TO erp_app, erp_reader;
\connect erp_optimisation_prod
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO erp_app;
GRANT USAGE ON SCHEMA public TO erp_reader;
ALTER ROLE erp_reader SET default_transaction_read_only = on;
ALTER ROLE erp_reader SET statement_timeout = '5s';
```

The app role owns its dedicated database/tables because approved index creation and isolated benchmark schemas need those rights. It does not need superuser, CREATEDB, CREATEROLE, replication or BYPASSRLS. This is still a powerful administration account; isolate this database from unrelated applications.

## Configure and initialize hosted mode

1. Copy `.env.production.example` to `.env.production`. Keep both the file and deployment credentials private. Source control ignores `.env.production`.
2. Set `APP_ENV=production`, both database URLs, and `PUBLIC_BASE_URL=https://your-real-host`. URL-encode password characters. Writer and reader URLs must point to the same host, port and database and use distinct accounts.
3. Generate `SECRET_KEY` using `python -c "import secrets; print(secrets.token_hex(32))"`; save the result privately. Do not use the placeholder. The key must stay stable across server processes/restarts; rotation signs out existing sessions.
4. Keep `ERP_BIND_HOST=127.0.0.1`, `ERP_PORT=8080` and `ERP_TRUSTED_PROXY=127.0.0.1` when the HTTPS proxy runs on this host. Wildcard proxy trust is rejected. A remote proxy requires its exact peer IP and a firewall restricting access to the backend.
5. In the initialization terminal, select the separate configuration:

```powershell
$env:ERP_ENV_FILE = (Resolve-Path .env.production).Path
.\venv\Scripts\python.exe scripts\init_db.py
.\venv\Scripts\python.exe scripts\create_user.py --username admin --role Admin
.\venv\Scripts\python.exe scripts\create_user.py --username analyst --role Analyst
```

After tables exist, run this grant as the app owner or maintenance account connected to the new database:

```sql
GRANT SELECT ON public.departments, public.employees, public.customers,
public.suppliers, public.products, public.orders, public.order_items,
public.inventory, public.payments, public.transactions TO erp_reader;
```

The reader must have no access to users, login throttles, recommendations, archive/support tables or arbitrary schema creation. Do not grant SELECT ON ALL TABLES to this account. Rerun initialization for additive schema updates, using a backup first. Incompatible existing column layouts need a reviewed migration; `init_db.py` is not a general migration framework.

## HTTPS, startup and restart management

The included `deploy/Caddyfile` forwards your real hostname to the loopback Waitress server. Install Caddy from its official distribution and set `ERP_HOST` to the hostname in `PUBLIC_BASE_URL`. Configure DNS, certificates and network routing for your environment. Caddy's public certificate flow normally needs the domain to resolve to the server and ports 80/443 to reach Caddy. An internal-only deployment may need an organization-managed certificate. See the [official Caddy reverse-proxy guide](https://caddyserver.com/docs/quick-starts/reverse-proxy).

```powershell
# In the inner application folder, with the production env selected:
.\venv\Scripts\python.exe scripts\deployment_check.py --production
.\serve-production.ps1
# In the separately managed proxy process/service:
$env:ERP_HOST = 'your-real-host'
caddy run --config .\deploy\Caddyfile
```

`serve-production.ps1` selects `.env.production` and forces production mode. The launcher refuses unsafe configuration or failing checks. Secure cookies require users to browse the **HTTPS** hostname; signing in directly through loopback HTTP is not a hosted-mode workflow. Flask validates allowed hosts, and Waitress accepts forwarded identity/scheme headers only from the configured proxy. See [Waitress proxy settings](https://docs.pylonsproject.org/projects/waitress/en/stable/arguments.html).

For unattended Windows operation, use an approved Windows service wrapper or Task Scheduler. With Task Scheduler: create a task under a dedicated restricted Windows account, trigger at startup, run `powershell.exe -NoProfile -File "<absolute-path>\serve-production.ps1"`, set the working folder to the inner project directory, prevent duplicate instances and configure restart-on-failure. Manage the PostgreSQL and HTTPS proxy services separately. Capture server output, rotate logs and monitor readiness; this repository does not install or alter machine services. Restrict file ACLs so only the service account and administrators can read environment files/backups. The app account needs no Windows administrator rights.

## Backup and recovery

```powershell
# From the inner folder. Uses configured PostgreSQL credentials without putting
# passwords in command-line arguments. Defaults to .local/backups/.
.\venv\Scripts\python.exe scripts\backup_database.py
# Optional: restore into a generated temporary DB, validate, then remove only it.
# This requires a maintenance account with CREATEDB.
.\venv\Scripts\python.exe scripts\backup_database.py --verify-restore
# If tools are elsewhere, add: --pg-bin 'C:\Program Files\PostgreSQL\17\bin'
```

Backups use PostgreSQL custom format and refuse an existing output filename. The optional restore rehearsal accepts no destination database, so it cannot restore over production. It checks the mapped schema, relationships and order/payment arithmetic. Normal production backup accounts may dump successfully but lack CREATEDB; run restore rehearsals under an approved maintenance account in a recovery environment.

The script saves data/schema and excludes role ownership/grants. Back up role grants, private environment configuration, TLS settings and service definitions separately. Backup files contain application/ERP data and are **not encrypted by this script**. Store protected, encrypted off-machine copies and set a retention policy. A successful backup without an independently exercised restore is insufficient recovery evidence.

## Release checks and rollout

1. Back up the deployed database and retain the previous code/dependency set.
2. Run the full tests against disposable databases on a separate test machine/database account. Production runtime roles deliberately cannot create test databases.
3. Run `pip check`; install `requirements-dev.txt` in the build/test environment and run `python -m pip_audit` against current advisories. The included audit is time-specific, not a permanent guarantee.
4. Stop the old app, install the tested requirements, run additive initialization, grant reader access only where intended, and run `deployment_check.py --production`.
5. Start the managed app/proxy. Check liveness/readiness, HTTPS login, analyst restrictions, explorer, an actual read-only plan and evidence export. Avoid a live index/archive mutation merely as a health check.
6. Monitor failures and database load. Schedule index benchmarks in a maintenance window because SHARE locks prevent concurrent writes during controlled comparisons.
7. For rollback, return to the prior compatible code/dependencies and reassess additive schema compatibility. Restore a backup only through an approved recovery plan; do not blindly replace a live database.

This release's Windows WSGI path, security flow, restricted-role rehearsal and backup restore were checked locally. Real DNS/TLS, service installation, firewall policy, current OS/runtime/database patching, production-scale load and your organization's security review remain operator deployment steps. These are not claimed as completed by the source-code changes.
