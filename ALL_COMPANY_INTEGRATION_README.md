# V4Career — Unified Company Collector Bundle

This bundle combines the uploaded full V4Career project with the latest Infosys API collector and concurrent structured-collector runner. It keeps the existing Flask UI and repository/database layer rather than rebuilding them.

## Company sources in the catalog
The catalog includes TCS, Infosys, Wipro, HCLTech, Accenture, Cognizant, Capgemini, Amazon, Microsoft, Google, IBM, Adobe, Zoho, Freshworks, and Paytm.

## Important distinction
- **Company catalog entry** means the official career site is configured as a starting point. It does not guarantee that the site exposes public structured job data.
- **Infosys** has a dedicated public search API adapter. The adapter was previously tested locally by the user against the live endpoint (100 unique jobs and 3 official job URLs returning HTTP 200).
- **Other companies** use the existing conservative schema.org `JobPosting` collector unless a separate adapter is implemented and validated. A site may return zero jobs if it uses client-rendered content, a different API, anti-bot protection, or does not publish JSON-LD. This bundle does not falsely label those sources as verified API integrations.
- The concurrent batch runner can reduce total wall-clock time, but concurrency is bounded and does not bypass site rate limits or access restrictions.

## Install and test (PowerShell)
1. Extract the ZIP into a new folder; keep the current working project and database backup.
2. Copy your own local `.env` into the project root only if needed. The ZIP deliberately excludes `.env` and secrets. Do not upload `.env`.
3. Activate your existing Python environment and install dependencies if needed:
   `python -m pip install -r requirements.txt`
4. Run offline tests first:
   `python -m pytest -q`
5. Test only Infosys without saving records:
   ```powershell
   @'
   from collectors.company_career_catalog import COMPANY_CAREER_BY_KEY
   from collectors.company_career_structured import collect_structured_jobs
   jobs, stats = collect_structured_jobs(COMPANY_CAREER_BY_KEY["INFOSYS"], max_results=10, timeout=30, max_pages=10)
   print("jobs:", len(jobs))
   print(stats)
   '@ | python -
   ```
6. Run a single-company collection only after reviewing `.env` database settings and confirming the target database is the intended local/test database. The CLI collection runner writes records.

## Collect companies
- One company, with persistence: `python scripts/run_company_career_structured.py --source INFOSYS --max-results 100`
- All catalog companies concurrently, with persistence: `python scripts/run_company_careers_structured_batch.py --max-results 50 --workers 3`

The batch runner writes to the configured database. Start with one company in a local/test database before using the all-company batch. The structured batch will report failures and may report zero jobs for sources without publicly exposed JSON-LD.

## Not yet claimed
This bundle does not claim that all 25 companies have verified, company-specific API adapters, nor that all 15 return live job data. Amazon, Wipro, TCS, and the other sources still require source-specific endpoint research and live validation where the generic collector cannot find genuine job postings.
