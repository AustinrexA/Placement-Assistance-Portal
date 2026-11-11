# V4Career client upgrade (Version 2 base)

## Install on Windows

1. Extract this ZIP into a new folder; do not overwrite your current project.
2. Open PowerShell in `V4Career_UI_Upgrade`.
3. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env`, then set the local database connection, `FLASK_SECRET_KEY`, `ADMIN_USERNAME`, and `ADMIN_PASSWORD_HASH`. Do not commit `.env`.
5. Run the existing schema/migrations required by your database, then start the app:

   ```powershell
   python -m flask --app app run --debug
   ```

6. Open `http://127.0.0.1:5000`.

## Implemented in this delivery

- Master checkbox is positioned within each sidebar heading and supports checked/unchecked/indeterminate states for the job portal list and career-site list.
- Company Career Sites is no longer a company-name filter. A separate list of employer career pages is seeded as `company_career` source records; those records are excluded from the Job Portal source list.
- The company-name text filter on the main Job Listings page is preserved.
- Dashboard has four KPI cards: active jobs, jobs added today, enabled collection sources, and failed collection runs today.
- Reports show source totals and recent collection runs.
- Existing job listing page markup and its filters/export controls are otherwise retained.

## Important configuration limits

The career-site entries are source placeholders, not ready-to-run scrapers. Each needs an authorized feed or a compatible scraper integration before collection can run. Selecting a career source does not launch scraping.

This build does not yet include a complete administrator UI for managing customer accounts and per-customer access expiry, nor full report-specific filters and filtered CSV/Excel exports for every requested report type. Those features require additional backend routes, a customer-account schema/migration, and authorization tests. Do not treat this delivery as satisfying those unfinished requirements.

## Safety

- No Render deployment or GitHub push is performed.
- The archive excludes `.env`, `.git`, `__pycache__`, and `.pyc` files.
- Back up your local database before applying any migration. No existing job records are deleted by the changes in this delivery.
