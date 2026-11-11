# V4Career Job & Career Opportunities Portal

V4Career is an existing Flask + MySQL job aggregation dashboard. This update preserves the current architecture and limits the Job Portal sidebar to the seven requested portals, adds a calmer orange accent and more readable typography, and keeps company-career integrations staged for one-by-one validation.

## What this update does

- Keeps the existing V4Career dashboard, authentication, sortable/paginated job table, filtering, Excel export, and collection history.
- Exposes only Foundit, Glassdoor, Indeed, Internshala, Naukri, TimesJobs and Wellfound in the Job Portal sidebar. Counts are database-backed; legacy sources remain in the database but are hidden from this UI.
- Displays whether a source has an Actor configured and explicitly approved. A portal with `0` jobs is not presented as having scraped records.
- Removes the unverified Companies sidebar group. Company career sources are staged separately and should be added to the UI one at a time after a live collection is verified.
- Returns role, location, and experience options from actual records, constrained by the other selected facets (including sources and companies).
- Uses the same company selections for job listing and Excel export.
- Provides a generic Apify adapter that can be configured per Actor, because each Actor can have a different input schema.
- Runs configured portals sequentially and skips sources without an Actor and explicit approval. A lock prevents overlapping multi-source batches.
- Stores normalized records with URL-based deduplication and collection-run summaries.

## Important: a visible portal is not proof of a working live collector

The UI is intentionally limited to seven requested portals. Collection is only active after you configure and validate an appropriate API, permitted feed, or Apify Actor for each portal. Do not copy one Actor ID to all portals: Actors have source-specific inputs and outputs. For every Actor, inspect its current input schema, output fields, price, terms, rate limits, and the source's rules for collecting and republishing job data. Some sources restrict automated collection or reuse. The approval flags intentionally default to `false`.

Apify's documented API runs an Actor, waits for the run, and retrieves items from its dataset. See [Apify run documentation](https://docs.apify.com/actors/running) and [dataset-items API](https://docs.apify.com/api/v2/actor-run-sync-get-dataset-items-post). Wellfound's [Terms](https://wellfound.com/terms) restrict automated harvesting/scraping unless expressly permitted; do not enable it unless your access method is authorized.

## Installation (Windows 11 / VS Code)

1. Back up your existing project folder and database before replacing files.
2. Extract this ZIP into `C:\Users\<your-user>\Downloads\job-portal-phase3` or another folder of your choice.
3. Create/activate a virtual environment:

   ```powershell
   py -m venv venv
   .\venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and fill in your own local configuration. Do not send `.env` or tokens to anyone, and never commit it to Git.
5. Ensure the existing MySQL database and the `sources`, `jobs`, and `collection_runs` tables are present. This project does not silently recreate or delete existing job records.
6. Start the app:

   ```powershell
   python app.py
   ```

7. Sign in using your locally configured admin credentials and check `/api/health` while authenticated or use the dashboard health indicator.

## Configuration

### Required application settings

- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `FLASK_SECRET_KEY`: set a random secret of at least 32 characters in production.
- `ADMIN_USERNAME` and `ADMIN_PASSWORD_HASH`: the hash must be generated locally using Werkzeug password hashing. Never store a plaintext admin password in `.env`.
- `COOKIE_SECURE=true` when deployed behind HTTPS.

Example local password-hash generation (run locally in your virtual environment):

```powershell
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash(input('New admin password: ')))"
```

Paste the generated hash into `.env` as `ADMIN_PASSWORD_HASH`. Do not paste it into chat.

### Configure one Apify Actor

1. Check that the Actor is allowed for your intended use, and review the Actor's input/output schema and price.
2. Add the token locally as `APIFY_API_TOKEN`.
3. Set the correct Actor ID, for example `APIFY_ACTOR_INDEED=owner~actor-name`.
4. Set `APIFY_ACCESS_APPROVED_INDEED=true` only after confirming authorization and permitted reuse.
5. If the Actor input schema differs from the common `{keyword, location, maxItems}` shape, set `APIFY_INPUT_INDEED` to a JSON object matching that Actor's documented schema. The following placeholders are supported: `{keyword}`, `{location}`, `{max_results}`.
6. Test one source with a small result limit before enabling scheduled runs:

   ```powershell
   python scripts/run_source_apify.py --source indeed --keyword "Software Engineer" --location "Chennai" --max-results 3
   ```

For Naukri, the legacy `APIFY_NAUKRI_ACTOR_ID` setting is still supported, but the explicit `APIFY_ACCESS_APPROVED_NAUKRI=true` flag is required. The generic runner is preferred for consistent configuration and source naming.

### Run all configured and approved sources

```powershell
python scripts/run_configured_sources.py --keyword "Software Engineer" --location "India" --max-results 20
```

The runner processes sources sequentially. A source without both an Actor ID and its explicit approval flag is skipped. A failed source is recorded in the summary and does not prevent later sources from running. Every source should be tested individually before enabling a recurring batch.

## Daily collection on Windows

Use Windows Task Scheduler only after the individual collectors are reliable:

1. Create a task that runs under the Windows account that owns the project and virtual environment.
2. Program: `C:\Users\<your-user>\Downloads\job-portal-phase3\venv\Scripts\python.exe`
3. Arguments: `scripts\run_configured_sources.py --keyword "Software Engineer" --location "India" --max-results 20`
4. Start in: the project root folder.
5. Set the task to run daily at a time appropriate for your workload.
6. In Task Scheduler settings, choose **Do not start a new instance** if the task is already running.
7. Keep run logs and review failures; do not assume scheduled collection is active until you verify a successful run in `collection_runs`.

The runner has an additional process lock, but the scheduler's no-overlap setting should also be enabled. Deployment to a Linux/container host requires a scheduler appropriate to that host; do not copy the Windows instructions unchanged.

## Data and production safeguards

- Back up MySQL before migrations or changing deduplication keys.
- Do not delete old jobs automatically until a retention/expiry policy is agreed and tested.
- Counts in the sidebar reflect stored database rows, not the number of raw results returned by an Actor run.
- Collection history records the valid normalized records passed to persistence; inspect source-specific logs to see rejected records.
- Duplicate prevention depends on the database's source-scoped unique URL-hash constraint. Confirm that constraint exists in the current database before deployment.
- Keep the database user least-privileged; do not use the MySQL root account for the application.
- Use HTTPS, a stable secret key, secure cookies, server-side logs, backups, and a tested restore procedure in production.
- Restrict admin access and configure monitoring for database failures, repeated collector failures, and unusually low collection volume.

## Tests and validation

Run locally after installing dependencies:

```powershell
python -m pytest -q
node --check static\app.js
python -m py_compile app.py collectors\*.py collectors\sources\*.py scripts\*.py
```

The current execution environment used to prepare this archive did not have Flask/MySQL dependencies or access to your database/Apify account, so live DB integration and real portal collection could not be verified here. Syntax checks and dependency-free normalization/catalog tests were run; run the full suite and a one-source database smoke test locally before production.

## Security note

The source archive uploaded for this update contained a `.env` file and Git metadata. This output archive deliberately excludes both. Because credentials in an uploaded archive should be treated as potentially exposed, rotate any database password, Apify token, Flask secret, or other credential that was present in that file/history, then update your local `.env`. Never include `.env`, `.git`, virtual environments, logs, or API tokens in project ZIPs.

## One-time legacy source-name check

Older runs may have stored Naukri jobs under `Naukri via Apify`. Before using the new 25-source counts, run this read-only check after configuring `.env`:

```powershell
python scripts/normalize_source_names.py
```

If it reports legacy aliases, back up the database and rerun with `--apply` to merge those records into the canonical Naukri source without removing unique job records. Do not use `--apply` before taking a backup.

## Company career collection update

A built-in structured collector now supports the 15 company sources in `collectors/company_career_catalog.py`. It accepts only `schema.org/JobPosting` JSON-LD on configured official career hosts and India-indicating locations. It will not turn a hiring-program page or generic career copy into a vacancy. Since some career sites render jobs through JavaScript or a separate ATS, the collector may legitimately return zero results until an official ATS hostname is verified or an approved Apify Actor is configured.

Run one source first:

```powershell
python scripts/run_company_career_structured.py --source TCS --max-results 10 --max-pages 20
```

Run all catalog sources:

```powershell
python scripts/run_company_careers_structured_batch.py --max-results 50 --max-pages 60
```

Optional official ATS hostnames can be configured per source with `CAREER_ALLOWED_HOSTS_<KEY>` in `.env`; verify the host from the company's official website before adding it. See `README_APIFY.md` for details and the optional Apify fallback. These commands perform live HTTP requests and write collection-run/job records to the configured database; use a local/test database first. No live collection was run as part of this code change.

Run the test suite from the project root:

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
```

Use `.env.example` as a placeholder template only. The actual `.env` file and all credentials are excluded from the distributed project package.
