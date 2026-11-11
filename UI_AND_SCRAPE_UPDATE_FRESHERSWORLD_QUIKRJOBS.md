# V4Career UI and collection update — Freshersworld + QuikrJobs

## Changes
- Added Freshersworld and QuikrJobs to `UI_PORTAL_KEYS`; both appear in the Job Portal UI when their Actor token/approval configuration is present.
- Kept National Career Service (NCS) hidden from the UI for now.
- Freshersworld defaults request up to the actor's supported five pages.
- QuikrJobs maps India/Bengaluru location inputs to the tested supported city name `Bangalore`, and requests up to five pages based on `--max-results`.
- No database job rows are deleted by these changes.

## Run collection
Run from the V4Career project root after confirming `.env` has `APIFY_API_TOKEN` and `APIFY_ACCESS_APPROVED_FRESHERSWORLD=true` and `APIFY_ACCESS_APPROVED_QUIKRJOBS=true`. Use 100 as a practical batch size; the actor may return fewer jobs due to its own supported pages, availability, or result limits.

```powershell
python scripts/run_source_apify.py --source Freshersworld --keyword "Software Engineer" --location India --max-results 100; python scripts/run_source_apify.py --source QuikrJobs --keyword "Software Engineer" --location "Bangalore, India" --max-results 100
```

`--max-results 100` is a requested cap, not a guarantee that 100 jobs will be found or saved. Check each run's `found`, `inserted`, and `updated` counts.
