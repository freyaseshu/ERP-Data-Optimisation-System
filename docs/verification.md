# Windows release verification — 1 November 2026

## Result

**180 tests passed; 0 failures, 0 errors and 0 skipped**, in **82.59 seconds**. The final report is `artifacts/test-results.xml`. The app is running through Waitress at **http://127.0.0.1:8080**. The older development-server process used for the earlier work was stopped.

```powershell
.\venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --junitxml=artifacts/test-results.xml
```

The 150 earlier feature/workspace checks remain covered. This review adds 25 deployment/security cases and five query-policy cases (custom/qualified operators, sampling rejection and preserved BETWEEN/NOT BETWEEN support). The final full run used the upgraded dependencies, not the old Flask environment.

## Review findings fixed

| Finding | Change and verification |
|---|---|
| Development server was the only launch path | Added Waitress server, loopback defaults, bounded requests/threads, proxy validation, preflight and Windows launchers. Actual Waitress startup on port 8080 passed. |
| Browser mutations lacked CSRF tokens | Flask-WTF protects login, logout, forms and JSON requests. Login/meta tokens and AJAX headers are integrated. Missing/incorrect tokens are tested; browser SQL analysis succeeds with valid tokens. |
| Unlimited login attempts | Shared PostgreSQL account/IP limits, atomic counters, expiry and HMAC keys. Limit/expiry/IP tests passed. |
| Stale account sessions remained usable | Current database accounts/roles are checked; deleted-account sessions are revoked. Thirty-minute signed sessions and POST-only logout are tested. |
| Production configuration could use development defaults | Hosted mode rejects missing/weak explicit secrets, insecure public URLs/cookies, disabled CSRF and absent reader configuration. Host rejection and secure HTTPS test cookies passed. |
| No deployment readiness signal | Added minimal unauthenticated liveness/readiness and a detailed read-only CLI preflight. Schema/connection failures return safe errors. |
| Inline handlers prevented a strict script policy | Added CSP nonces and replaced explorer/benchmark inline event attributes with listeners. Browser table selection, search, sort and paging all passed. |
| Standalone recommendation status committed separately from its index | Index, measurement evidence and successful status now share a transaction. An injected final-status failure rolls back the index and performance log. |
| Unbounded report history and inconsistent custom dates | Reports/CSV cap selected measurements at 1,000 with a visible scope/truncation notice; custom date filters require ISO dates. Tests cover both. |
| Unhandled failures could yield inconsistent API responses | Safe JSON errors, no-store responses and request IDs; database-unavailable dashboard compatibility retained. Internal exception text does not escape. |
| SQL operator/sampling paths were not explicitly restricted | Custom/qualified operators and table sampling are rejected; ordinary built-in operators and BETWEEN remain supported. |
| No exercised recovery path | Added a private PostgreSQL backup command and optional restore into a generated disposable database. Full local backup/restore rehearsal passed. |

## Dependency verification

`pip-audit` initially reported advisories affecting installed pip 25.0.1, pytest 8.4.2 and python-dotenv 1.0.1. They were updated to patched versions. Flask was upgraded for the production security configuration; Waitress and Flask-WTF were added.

The final installed environment scan returned **No known vulnerabilities found**. Evidence: `artifacts/dependency-audit-final.json`. `python -m pip check` returned **No broken requirements found**. This is a time-specific package advisory check, not an operating-system/database vulnerability scan or penetration test.

Verified primary versions include Flask 3.1.3, Werkzeug 3.1.9, Flask-WTF 1.3.0, Waitress 3.0.2, python-dotenv 1.2.4, pytest 9.2.0 and pip 26.2.2. SQLAlchemy/psycopg compatibility remained covered by real PostgreSQL integration tests. Python compilation and every `static/js` syntax check passed.

## Restricted production-role rehearsal

A dedicated fixture created new generated test roles/database, initialized the schema with a non-superuser owner, granted a distinct nonprivileged reader access only to the ten ERP tables, and ran production preflight successfully. It exercised HTTPS login with a real CSRF token, Secure/HttpOnly cookies, host validation, reader analysis and readiness. All generated roles and the test database were removed. This does not configure a real hosted domain or change the prepared demo owner's privileges.

The prepared configuration intentionally remains in local presentation mode. `deployment_check.py` succeeds for that mode. `deployment_check.py --production` correctly **fails** because the demo configuration is not production mode and uses a privileged local owner. Follow `docs/deployment.md` to provision separate hosted roles and HTTPS before switching modes. Do not describe the prepared demo credentials as production-safe.

## Backup/restore and data integrity

Executed `scripts/backup_database.py --verify-restore`. It created a 1,473,111-byte custom-format dump under `.local/backups/`, restored it into a fresh generated `erp_restore_...` database, checked every mapped table/column and validated **77,220 ERP records**. All PK/FK, order/item arithmetic and payment-total checks passed. The generated restore database was removed; the source database was not replaced. Role grants/credentials are deliberately excluded from the dump and require a separate protected operational backup.

The demo schema now has **18 mapped tables** (ten ERP and eight support tables). `scripts/init_db.py` applied the additive login-throttle table without replacing data. Generated `database/schema.sql` includes mapped tables and explicit model indexes.

## Browser and server checks

Verified on Waitress at port 8080 using the existing local Admin account:

- Login with a rendered CSRF token and the new signed session.
- Dashboard showing actual 77,220 ERP records and 18 tables.
- Explorer table selection, Chicago search (433 matching customers), descending ID sort and page-two navigation.
- Actual EXPLAIN ANALYZE through the CSRF-protected JSON path; the prepared city query used the existing index and returned 433 rows.
- Reports, actual stored results/trend, new scope notice and completed CSV download.
- Workspace loading the prior assessments on the new server.
- No warning/error console messages reported during the checked release browser session.

The browser automation tool stalled while waiting for the CSV download; the download completed. That tool delay is not treated as an application benchmark. Visual proof is saved separately under `artifacts/`.

## Deployment status and remaining work

**Ready for the documented local Windows presentation.** Hosted deployment preparation is implemented and locally rehearsed, but no external server was deployed. Actual DNS/TLS, reverse-proxy operation, Windows service-account/file permissions, managed startup, firewall policy, monitoring and current OS/Python/PostgreSQL security patching remain operator steps. The local executed interpreter is Python 3.12.10; hosted deployments should use a maintained patched runtime/server.

The four supplied research gaps remain implemented at the documented local-platform scope. There are **16 limitation entries: 8 Implemented and 8 Partially Implemented**. Partitioning remains a temporary-copy experiment; archiving stores header snapshots without space reclamation; mixed updates roll back and exclude commit latency; general automatic query rewriting, MFA/SSO, continuous database collection, predictive ML, cold-cache isolation and production-scale capacity validation remain outside the tested scope. Controlled benchmarks can block ERP writes and belong in a maintenance/demo environment.

Full explanations: `docs/feature-guide.md`. Deployment and recovery: `docs/deployment.md`. Ordered demonstration/talk tracks: `docs/presentation-guide.md`. The earlier 150-test research-gap verification is preserved in `docs/verification-research-gaps-2026-11-01.md`; the original repair checks are preserved in `docs/verification-2026-10-21.md`.
