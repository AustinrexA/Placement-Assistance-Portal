# JobSpy direct-to-database integration

The project now includes `scripts/run_jobspy.py`. Unlike the earlier test collector, this script saves each completed search immediately through the existing `collectors.normalization.normalize_job()` and `collectors.repository.save_jobs()` functions. It uses the database configured in the project's local `.env` (currently Neon PostgreSQL in the user's setup).

## One-time setup

From the V4Career project root, activate the project's virtual environment if you use one, then install the updated requirements:

```powershell
python -m pip install -r requirements.txt
```

## Run and save directly to the configured database

```powershell
python scripts/run_jobspy.py --results-per-site 50
```

This is a live database-writing command. It does not require a separate CSV import. Every completed search is normalized and sent to the repository immediately. Existing rows are deduplicated/updated by the repository. A CSV copy is also retained under `jobspy_results`.

## Dry run (no database writes)

```powershell
python scripts/run_jobspy.py --results-per-site 50 --dry-run
```

## Optional posting-age filter

The installed JobSpy API version must support `hours_old` before enabling it. Use `--hours-old 72` to request jobs posted within roughly the last 72 hours. If the installed version does not accept that argument, the script should be updated to pass the option only after confirming the package API.

## Important

- The local `.env` controls which database is written to. The script does not automatically write to Render's production database unless its credentials are explicitly configured locally.
- The scraper may return fewer jobs than requested, and public job sites can rate-limit or change behavior.
- The five-minute cap stops launching new searches and terminates a search at the deadline. Completed searches are saved immediately; a search interrupted at the deadline may not return its partial results.
- `python-jobspy` is added to `requirements.txt`; install dependencies once after applying the project update.
