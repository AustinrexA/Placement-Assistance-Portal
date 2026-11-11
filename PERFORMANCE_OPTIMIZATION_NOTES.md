# V4Career performance optimization update

This update targets the slow first-page load shown in the browser Network panel.

## Changes

1. **Lazy-load Reports:** The report overview and detailed report no longer fetch data during initial page startup. They load when the user opens Reports. This avoids duplicate dashboard-statistics and source requests while landing on Dashboard.
2. **PostgreSQL connection pooling:** `collectors/db.py` now uses `psycopg_pool.ConnectionPool` for PostgreSQL/Neon and returns leased connections to the pool when existing code calls `connection.close()`. MySQL pooling behavior is unchanged.
3. **Configurable pool limits:** Defaults are `PG_POOL_MIN_SIZE=1`, `PG_POOL_MAX_SIZE=5`, `PG_POOL_TIMEOUT=8`, and `PG_POOL_MAX_LIFETIME=1800`. Adjust only after measuring Render concurrency and Neon connection limits.
4. **Additional safe indexes:** `database/performance_indexes_postgres.sql` now includes indexes for job creation dates and collection-run lookups by source/time. These are non-destructive `CREATE INDEX IF NOT EXISTS` statements.
5. **Dependency:** Requirements use `psycopg[binary,pool]` so Render installs the pooling package.

## Deploy and verify

1. Review the diff and keep the currently deployed revision available for rollback.
2. Deploy the code to a staging service first if possible.
3. Run the SQL statements in `database/performance_indexes_postgres.sql` once against the correct Neon database; index creation changes schema but does not alter job records.
4. Confirm `/api/health` returns healthy and verify job/source counts remain unchanged.
5. In DevTools Network, reload the Dashboard and verify that `/api/reports/jobs` and the report-only `/api/collection-runs?limit=8` request are not issued until Reports is opened.
6. Compare dashboard, job, filter, and report timings before/after. Cache is process-local, so cold and warm requests may differ.

## Validation notes

- `python -m py_compile app.py collectors/db.py` passed.
- `node --check static/app.js` passed where Node.js is available.
- The Python unit-test discovery run could not import `tests/test_api.py` in the local execution environment because Flask is not installed there. Run the full suite in the project's virtual environment after installing `requirements.txt`.
- Do not run database migrations or change job data as part of this performance update. Preserve the MySQL backup.
