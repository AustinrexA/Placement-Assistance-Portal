# Company career scraper setup

V4Career keeps company-career sources separate from general job portals. The Companies sidebar filters jobs already stored in the existing database; it does not launch a scrape when a checkbox is selected. Collection is run explicitly from the command line or through a reviewed scheduler.

## Current collection method

`scripts/run_company_career_structured.py` looks for schema.org `JobPosting` JSON-LD on the official career URLs in `collectors/company_career_catalog.py`. It only saves records that pass the collector's vacancy validation and India-location checks. Company catalog membership is not proof that live collection works for that company. Some career sites do not expose this data to ordinary HTTP clients, and some block requests.

TCS currently returns HTTP 403 on all four configured pages in the last reported local run. That is an access failure, not proof that there are no TCS vacancies. Do not work around access controls or save program descriptions as jobs. If a company needs an alternative, review an official public feed/ATS endpoint or a permitted Apify Actor's current input schema, output fields, terms and pricing first. Only then configure the per-company `APIFY_ACTOR_COMPANY_<KEY>`, `APIFY_INPUT_COMPANY_<KEY>` and `APIFY_ACCESS_APPROVED_COMPANY_<KEY>` values in the local `.env`. Never invent Actor IDs or commit tokens.

## Test one company

Use a separate local/test database in `.env` before running a collector, because collection writes to the configured database. Example for TCS:

```powershell
python scripts/run_company_career_structured.py --source TCS --max-results 10 --max-pages 20 --timeout 15
```

Run other companies individually by replacing `TCS` with `INFOSYS`, `WIPRO`, `HCLTECH`, `ACCENTURE`, `COGNIZANT`, `CAPGEMINI`, `AMAZON`, `MICROSOFT`, `GOOGLE`, `IBM`, `ADOBE`, `ZOHO`, `FRESHWORKS` or `PAYTM`. Do not run the batch until you have reviewed per-source access and test results.

## Batch run

After source-by-source verification, run:

```powershell
python scripts/run_company_careers_structured_batch.py --max-results 50 --max-pages 60
```

Review each source's pages attempted/fetched/blocked, valid jobs found, inserted/updated counts and run status. A zero-job result after successful page fetches means no qualifying structured vacancies were found; a result where no pages could be fetched is a failed run.

## UI behavior

The Companies sidebar displays company names and counts only. Its checkbox filters matching stored company-career source records in Job Listings. It does not scrape on checkbox click. The sidebar intentionally omits `Setup`, `Actor`, `Unverified`, and `JSON-LD` badges to keep the navigation clean; collector configuration and status remain a technical setup/testing concern, not a UI status claim.


## Infosys API collector and faster batch runs

Infosys uses its public career search API through the dedicated branch in `collectors/company_career_structured.py`; it does not require an Apify Actor. The following Python snippet is a read-only preview and does not connect to the database:

```powershell
@'
from collectors.company_career_catalog import COMPANY_CAREER_BY_KEY
from collectors.company_career_structured import collect_structured_jobs
jobs, stats = collect_structured_jobs(COMPANY_CAREER_BY_KEY["INFOSYS"], max_results=100, timeout=30)
print(stats)
print("Jobs returned:", len(jobs))
'@ | python -
```

To persist results, use the standard runner below only after reviewing the configured database settings in `.env`:

```powershell
python .\scripts\run_company_career_structured.py --source INFOSYS --max-results 100 --timeout 30
```

For a faster full catalog run, the structured batch runner supports a conservative worker pool (default 3, allowed 1-6):

```powershell
python .\scripts\run_company_careers_structured_batch.py --max-results 50 --workers 3
```

Use `--workers 1` for serial collection or when diagnosing source throttling. A source-specific preview is available via `--source INFOSYS`, but the runner writes results to the database; use `collect_structured_jobs` directly for a read-only preview.


## Official company collector smoke tests (India jobs)

Infosys is the only source currently marked verified in the UI. The following are
official-site candidates and must be tested before marking verified:

```powershell
python scripts/run_company_career_structured.py --source WIPRO --max-results 100 --max-pages 10 --timeout 30
python scripts/run_company_career_structured.py --source ACCENTURE --max-results 100 --max-pages 10 --timeout 30
python scripts/run_company_career_structured.py --source DELOITTE --max-results 100 --max-pages 10 --timeout 30
```

A successful process exit is not enough by itself: confirm `jobs_found` is greater
than zero, records are inserted/updated without database errors, and the saved
jobs appear in the UI. These candidates intentionally remain unverified until
those checks pass.


## Official company collectors (Infosys, Wipro, Amazon, Accenture)

Run one company at a time from the project root:

```powershell
python scripts/run_company_career_structured.py --source INFOSYS --max-results 100
python scripts/run_company_career_structured.py --source WIPRO --max-results 100
python scripts/run_company_career_structured.py --source AMAZON --max-results 100
python scripts/run_company_career_structured.py --source ACCENTURE --max-results 100
```

These commands use the existing V4Career database configuration and collector/repository pipeline. They do not require an invented Apify Actor ID. Infosys uses its public careers search API; Wipro reads its official India RSS feed; Amazon reads the official Amazon Jobs India search page; Accenture starts from its official India job-search route. The Wipro feed may currently contain no real vacancy items, and the Amazon/Accenture parsers must be considered unverified until the run output reports actual individual jobs. A zero-job run is reported as zero; it is not replaced with made-up or program-description records.
