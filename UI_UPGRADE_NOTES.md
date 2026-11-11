# V4Career UI and Source Display Upgrade

This project archive is based on the uploaded ZIP and includes these targeted changes:

1. Sidebar and main content use separate vertical scroll containers.
2. UI styling is refined with consistent surfaces, hover states, focus states, and typography polish while retaining the existing layout structure.
3. The source API avoids displaying a duplicate Naukri entry when the canonical Naukri row is empty and a populated `Naukri via Apify` row exists. It preserves database records and source IDs, and maps readiness to the Naukri collector configuration.

## Important database compatibility note
The uploaded archive's `app.py` uses MySQL-specific database operations (`mysql.connector`, `ON DUPLICATE KEY UPDATE`) and is **not the Neon PostgreSQL version** described in the continuation brief. This package is based on the uploaded archive and must not replace a newer Neon-backed working directory without first reconciling the database repository and SQL dialect. No database migration is run by this package.

## Run locally
1. Extract this ZIP into a new test folder.
2. Create a local `.env` from your own safe configuration; no `.env` or secrets are included.
3. Install dependencies using `python -m pip install -r requirements.txt`.
4. Configure the database and scraper credentials locally.
5. Run the app using the command already documented for your project, then verify Dashboard, Job Portal, source selection, filters, pagination, export, and authentication.
6. Run `python -m pytest -v`.

The ZIP intentionally excludes `.env`, `.git`, Python caches, and common local dump/backup files.
