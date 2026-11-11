# V4Career dashboard and salary-filter upgrade

## What changed
- Added a dedicated Dashboard page; Job Portal now opens the existing job listing workspace.
- Added MySQL-backed cards for new job records today, this week, this month, total jobs, scraper-reported records found/inserted today, enabled sources, and listings with salary data.
- Added source ranking and recent collection activity tables.
- Added salary range/currency/pay-period filters to job search and Excel export; salary is shown in the job grid when present.
- Added salary normalization for common actor field names and salary range text.
- Added a backward-compatible SQL migration. Existing jobs are retained and existing salary fields remain unknown until a collector returns salary data.
- Added `.env.example`. The live `.env` is intentionally excluded from the delivery ZIP to protect secrets.

## Local Windows / PowerShell rollout
1. Back up your project folder and MySQL database before updating.
2. Extract this ZIP to a new folder; do not overwrite your current working folder yet.
3. Copy your private `.env` from your existing project into the extracted project folder. Do not share it.
4. In MySQL Workbench, select the `job_portal` connection and run `scripts/migrations/20261014_add_salary_fields.sql` exactly once. The migration adds columns and an index; it does not delete or rewrite job rows.
5. Open PowerShell in the project folder and activate your existing virtual environment, if you have one. Otherwise run `python -m venv .venv`, then `\.venv\Scripts\Activate.ps1`, then `python -m pip install -r requirements.txt`.
6. Run `python -m py_compile app.py collectors\*.py scripts\*.py` and `python -m pytest -q`.
7. Start locally with `python app.py`, then sign in and check Dashboard, Job Portal, salary filters, Reports, and Excel export.
8. The default local cookie setting can remain `COOKIE_SECURE=false` only for local HTTP. Set `FLASK_ENV=production`, a random `FLASK_SECRET_KEY` (32+ characters), `COOKIE_SECURE=true`, `FLASK_DEBUG=false`, and production DB credentials when using HTTPS hosting.

## Metrics definitions
- Jobs added today/week/month count rows by `jobs.created_at`; the week starts Monday according to MySQL's database date/time.
- Scraper-reported jobs found and inserted count `collection_runs` summary fields by `started_at`. Found may include existing jobs, so it is intentionally not presented as unique newly added records.
- Source enabled count is a database configuration count, not a guarantee that a scraper is authorized or currently functioning.

## Salary behavior and limitations
- Salary filtering is applied in SQL and is included in Excel export. A min salary matches listings whose known upper bound reaches the requested minimum; a max salary matches listings whose known lower bound is below the requested maximum.
- Currency is never converted. Select the currency matching the salary source. Pay period can be specified to avoid comparing yearly and monthly amounts.
- Many job listings omit salary; those records do not match a salary-constrained query.
- Existing records remain salary-unknown until collected/upserted with salary fields. No scraper is automatically run by this upgrade.

## Deployment status
This package is prepared for local verification, not claimed to be deployed or production-verified. Run tests against your own MySQL schema and test login/filters/export before deploying. Use a production WSGI server (Waitress is included and works on Windows), HTTPS via the hosting platform or reverse proxy, a managed/private database connection, backups, and platform-managed secrets. On Windows, after installing requirements, run `waitress-serve --listen=127.0.0.1:5000 wsgi:app` behind a TLS reverse proxy for internet-facing deployment. Do not expose MySQL publicly or run Flask debug mode in production.
