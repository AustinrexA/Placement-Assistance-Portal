# V4Career free job collector (initial implementation)

This package adds `scripts/run_free_sources.py` and does not remove or modify the existing Apify or company-career collectors.

## Included source adapters

- Greenhouse public Job Board API: only employers added to `config/free_sources.json`.
- Lever public Postings API: only employers added to `config/free_sources.json`.
- Remote OK public feed.
- Jobicy public API.

The India filter is intentionally strict: a record is only accepted if its location fields mention India or a recognized Indian city. That means many worldwide-remote jobs are excluded unless the source declares India eligibility. A public feed can return zero India matches and that's a valid result.

**This is not a guaranteed 5,000 jobs/day source.** Public feed sizes and India-eligible results are outside V4Career's control. Do not count duplicate, malformed, non-India or stale listings toward the target.

## Safety

- Default is **dry-run**: no database writes.
- `--save` enables writes through the project's existing `collectors.repository.save_jobs`.
- No schema migration is needed for this first version.
- Configure `DATABASE_URL` using the project's existing `.env` locally or GitHub Actions secret. Never commit `.env`.
- Respect each source's current terms, attribution requirements, rate limits, and allowed use. Do not use this to bypass portal access controls.
- Do not run with `--save` against production until the dry-run output is reviewed.

## Install and run (Windows PowerShell)

From the project root:

```powershell
python -m pip install -r requirements.txt
python scripts/run_free_sources.py --source all --limit-per-source 50
```

That command is a dry-run and reports validated India-location jobs. To save after reviewing:

```powershell
python scripts/run_free_sources.py --source all --limit-per-source 50 --save
```

Test sources independently:

```powershell
python scripts/run_free_sources.py --source greenhouse --limit-per-source 20
python scripts/run_free_sources.py --source lever --limit-per-source 20
python scripts/run_free_sources.py --source remoteok --limit-per-source 20
python scripts/run_free_sources.py --source jobicy --limit-per-source 20
```

## Configure Greenhouse / Lever company boards

Edit `config/free_sources.json` with verified board identifiers, for example:

```json
{
  "greenhouse": [
    {"slug": "verified-board-token", "company": "Example Company"}
  ],
  "lever": [
    {"slug": "verified-lever-site", "company": "Example Company"}
  ]
}
```

These values are examples, not real company board IDs. Do not guess slugs: test the company board and confirm that it returns jobs for the company. Public APIs are per-employer; they are not global job-search APIs.

## What's next

1. Run a dry-run from your Windows environment and inspect each source's counts.
2. Configure verified Greenhouse / Lever boards and test again.
3. Check the database's actual `DATABASE_URL` connection and schema before using `--save`.
4. Add a GitHub Actions schedule only after the workflow is validated. Keep Apify enabled for sources that do not have a suitable, authorized free alternative.
5. Track `fetched`, `valid`, `unique`, `inserted`, and `updated` separately. `inserted` is the count closest to genuinely new jobs.

Naukri, Indeed, Foundit, Internshala, TimesJobs, Wellfound and other India-focused portals are not replaced by these APIs. Continue only through an authorized free feed or access method for each portal.
