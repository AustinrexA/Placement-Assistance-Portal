# V4Career dual-database compatibility

This development version supports MySQL 8 and PostgreSQL/Neon selected through `DB_ENGINE`. Existing UI, API, collectors and export behavior are intended to remain unchanged.

## Local test setup

1. Extract this ZIP into a new directory. Do not overwrite your existing project.
2. Create `.env` from `.env.example` and configure `DB_ENGINE=mysql` with the connection details for the isolated `job_portal_test` database. Never commit `.env`.
3. Install dependencies: `python -m pip install -r requirements.txt`.
4. Run `python -m compileall -q app.py collectors scripts tests` and `python -m unittest discover -s tests -v`.
5. Open the app and test `/api/health`, dashboard, job listing/search/filtering, company/report pages, Excel export, and one controlled collector run.
6. Verify counts before and after testing. Do not run normalization with `--apply` unless you explicitly intend to consolidate source aliases and have a fresh backup.

## Engine settings

- MySQL: `DB_ENGINE=mysql`, `DB_HOST`, `DB_PORT` (default 3306), `DB_NAME`, `DB_USER`, `DB_PASSWORD`. For a local non-TLS MySQL instance only, `DB_SSL_DISABLED=true`.
- PostgreSQL/Neon: `DB_ENGINE=postgres`, `NEON_HOST`, `NEON_PORT` (default 5432), `NEON_DB`, `NEON_USER`, `NEON_PASSWORD`, and optional `NEON_SSLMODE` (default `require`). If `DB_ENGINE` is absent, the app defaults to PostgreSQL to preserve the previous production behavior.

## Safety and verification limits

- `database/mysql_schema.sql` creates missing tables but is not a migration script and should not be applied blindly to a populated database.
- The PostgreSQL schema and the explicit MySQL-to-Neon migration utilities are retained.
- Do not point local tests at production credentials. Do not deploy until the full test suite and a real MySQL integration test pass.
- This package was syntax-checked in its preparation environment. Database integration and the full test suite still need to be run in an environment with project dependencies and access to the isolated test database.
