# V4Career Company Career Integration Update

## Implemented

- Added a built-in structured collector in `collectors/company_career_structured.py` for the 15 existing company sources.
- The collector only accepts schema.org `JobPosting` JSON-LD, requires an India-indicating location, checks employer identity when supplied, validates the job URL against the configured official host allowlist, deduplicates within a run, and skips generic program/career pages.
- Added TCS entry-level, NQT and Ignite/Smart Hiring discovery URLs. Those pages are discovery points only; they are not themselves treated as job records.
- Added `scripts/run_company_career_structured.py` for a single company and `scripts/run_company_careers_structured_batch.py` for all catalog companies.
- Hardened the optional Apify company runner so it rejects known landing pages, generic program titles, mismatched employer names, and URLs outside the configured official host allowlist. Missing Actor status no longer defaults to `active`.
- Added failure-run recording for unreachable official career pages using the existing MySQL/PostgreSQL repository helpers.
- Added company job counts and method labels to the Companies sidebar. A JSON-LD label is not a claim that the site has been live-verified.
- Added `.env.example` containing placeholders only and updated integration documentation.

## Test results

Passed:

- Python compilation for modified Python modules and `app.py`.
- Focused regression suite: **30 tests passed, 40 subtests passed** (`test_company_career_catalog.py`, `test_company_career_structured.py`, `test_normalization.py`, `test_source_catalog.py`, `test_db_compatibility.py`).

Blocked:

- Full `pytest -q` cannot collect `tests/test_api.py` in the current environment because Flask is not installed (`ModuleNotFoundError: flask`). Install project requirements and rerun the full suite.

Not tested:

- No live company websites, Apify Actors, or database were called during implementation.
- No database migration, production data change, or Render deployment was performed.
- Some company career pages may render jobs with JavaScript or on a separate ATS. Those sources require live validation and, when applicable, a verified hostname in `CAREER_ALLOWED_HOSTS_<KEY>` or a separately reviewed Actor configuration.

## Run locally

From the project root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env with your existing local DB settings; do not use production credentials for the first test.
python scripts/run_company_career_structured.py --source TCS --max-results 10 --max-pages 20
python -m pytest -q
```

Run all companies only after testing one source and confirming that `.env` points to a local/test database:

```powershell
python scripts/run_company_careers_structured_batch.py --max-results 50 --max-pages 60
```

The live collection commands make HTTP requests and write collection history/job records to the configured database. They were not run while creating this package.

## Current staged scope (2026-10-21)

Only Infosys, Amazon and Wipro remain in the company-career catalog while they are integrated individually. Infosys has a dedicated public-search API adapter and its field mapping has been updated for the observed API schema. Amazon and Wipro still require separate live collection verification; catalog presence alone must not be described as a successful collector. The Companies sidebar group is intentionally hidden until each company is validated.


## 2026-10-21 — Company collector and sidebar update

- Company sidebar now lists every configured official company source, even when its collector has not yet passed live verification. The count remains the number of stored job records for that source.
- Amazon collector now tries the official `amazon.jobs/en/search.json` search response and normalizes returned job records, with HTML job-card fallback.
- Wipro collector keeps the official RSS feed, rejects placeholder entries, and falls back to the official SuccessFactors `/search/?q=&locationsearch=India` results page when the feed contains no individual vacancies.
- Accenture listing parsing accepts the existing `jobdetails?id=` form and common official careers job-detail path variants.
- Infosys collection logic is unchanged.
- Live collection still needs to be run from the user's configured environment to confirm the current public responses; this environment has no DNS/network access to those career sites. Mocked tests validate parsing and normalization but are not evidence of live vacancies being inserted.
