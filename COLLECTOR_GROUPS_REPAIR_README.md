# V4Career Collector 1/2/3 repair package

This package is a targeted repair of the uploaded V4Career project. It does not guarantee that every third-party portal will return 1,000 jobs: each Actor controls its own schema, pagination, access, and plan limits.

## Important safety
- The uploaded `.env` was deliberately **not copied** into this ZIP because it contains credentials. Copy your own `.env` from your local backup into this project folder; never share it or commit it.
- If the uploaded `.env` contained live credentials, rotate the Neon/database password, Apify token, Flask secret, and any other exposed credentials.
- Keep `APIFY_ACCESS_APPROVED_<PORTAL_KEY>=false` until you have checked that Actor's current input schema, terms, and pricing in Apify.
- `--max-results 1000` is a target, not a guarantee and not a promise that the Actor plan allows 1,000 records.
- Collector groups run every portal in that group, so a single command may start several Actor runs and may incur usage charges. Start with `--max-results 10`.

## Run from PowerShell
Open PowerShell in the project root (the folder containing `app.py`).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `.env` from `.env.example` and fill in your own database connection and Apify settings locally.

Start with one small test per group:

```powershell
python scripts/run_source_apify.py --source COLLECTOR1 --keyword "Software Engineer" --location India --max-results 10
python scripts/run_source_apify.py --source COLLECTOR2 --keyword "Software Engineer" --location India --max-results 10
python scripts/run_source_apify.py --source COLLECTOR3 --keyword "Software Engineer" --location India --max-results 10
```

Only after checking run cost, status, and saved jobs, increase the target:

```powershell
python scripts/run_source_apify.py --source COLLECTOR1 --keyword "Software Engineer" --location India --max-results 1000
python scripts/run_source_apify.py --source COLLECTOR2 --keyword "Software Engineer" --location India --max-results 1000
python scripts/run_source_apify.py --source COLLECTOR3 --keyword "Software Engineer" --location India --max-results 1000
```

Each group continues through the remaining portals when a portal fails and reports successes and failures at the end. A nonzero exit code means at least one portal in the group failed; check the individual error in the JSON output and logs.

## Changes included
- Fixed NCS default input so `maxItems` never exceeds the observed Actor schema ceiling of 100; related request limits are bounded too.
- Added source-scoped external-ID lookup before INSERT to prevent a duplicate external ID from aborting the whole batch. Existing rows are updated; no job rows are deleted.
- Updated existing-job persistence to refresh the URL hash when a stable external ID has a changed URL.
- Collector group token lookup accepts both `APIFY_API_TOKEN_COLLECTOR1` and `APIFY_API_TOKEN_COLLECTOR_1` naming conventions (same for groups 2 and 3).
- Kept per-portal approval flags and Actor schema configuration. These cannot be bypassed by the patch.

## Known limits that code cannot eliminate
- Some portals block scraping (403/404/TLS challenges), change Actor input schemas, require API keys/approval, or restrict output on free plans.
- Jooble previously returned only 10 items on the free Actor plan. A request target of 1,000 cannot override that.
- A portal's returned count can be greater than the number inserted because many returned jobs may already exist and be updated.
- Review each Actor's pricing and input schema before running large batches.
