# Apify + Naukri integration for Phase 3

## Before running
- Keep your existing Phase 2/3 MySQL tables.
- Put `APIFY_API_TOKEN` in the project-root `.env`.
- The token must never be committed to Git or pasted into chat.
- Check the Actor's current pricing, input schema, source terms, and your company's permission to collect/store/reuse results before running.

## .env
Add to your existing root `.env`:
```dotenv
APIFY_API_TOKEN=your_real_token_here
APIFY_NAUKRI_ACTOR_ID=automation-lab~naukri-scraper
APIFY_ACCESS_APPROVED_NAUKRI=false
```
Do not replace the existing DB settings.

## Install
```powershell
pip install apify-client
```
Also add `apify-client` to `requirements.txt`.

## Run a small test
From the project root, run:
```powershell
python scripts/run_naukri_apify.py --keyword "Python Developer" --location "Chennai" --max-results 1
```

This script uses the existing `collectors.normalization.normalize_job` and `collectors.repository.save_jobs` functions. It expects the Phase 3 project files and Phase 2 database tables to already exist.

The Actor is third-party and is not an official Naukri integration. Start with one result, review output and cost in Apify, and scale only after the data and permitted use have been validated.


## Built-in candidate Actors (review before enabling)

The generic runner includes these candidate Actor IDs and source-specific input defaults, checked against their Apify Store pages on 2026-10-14. They are prefilled as convenience defaults in `.env.example`; no Actor is executed until its approval flag is explicitly enabled:

- Indeed India: `unfenced-group~indeed-in-scraper`
- Foundit: `deriverge~foundit-jobs-scraper`
- Internshala: `automation-lab~internshala-scraper`
- TimesJobs: `unfenced-group~timesjobs-scraper`
- Wellfound: `cprussin~wellfound-jobs`

They are community-maintained, can change or stop working, and may charge usage fees. Do not treat listing a source in the dashboard as proof that collection has succeeded. Before enabling a source, open its Store page, review the current input/output schema, pricing and applicable terms, then run a small test. Set `APIFY_ACCESS_APPROVED_<PORTAL_KEY>=true` only after you have decided to use that Actor and verified that your intended collection and reuse are permitted. These approval flags default to `false`; the batch runner skips sources without explicit approval.

Default input schemas are selected per portal by `scripts/run_source_apify.py`. To override one, set `APIFY_INPUT_<PORTAL_KEY>` to a single-line JSON object matching the selected Actor's current schema. Supported placeholders are `{keyword}`, `{location}`, and `{max_results}`. Internshala's selected Actor accepts a keyword and job/internship mode but has no location input; use V4Career's dashboard filters to narrow the stored results by location.

The default Actor IDs are also written to `.env.example` for convenience. Your existing `.env` is intentionally not included in ZIP files; copy only the relevant variable names/values into your local `.env` and never share your token.

## Company career-site collectors

V4Career includes a separate company-career catalog and configurable Apify runner. It deliberately does **not** assume that one Actor's input format works for every employer site. Before enabling any source, confirm the site's terms and the selected Actor's current input/output schema and pricing.

For each company, add three variables to your local `.env`. Example for TCS (replace the placeholder Actor and JSON with an Actor you have reviewed):

```dotenv
APIFY_ACTOR_COMPANY_TCS=owner~your-reviewed-actor
APIFY_ACCESS_APPROVED_COMPANY_TCS=false
APIFY_INPUT_COMPANY_TCS={"startUrls":[{"url":"{start_url}"}],"maxRequestsPerCrawl":20}
```

`APIFY_INPUT_COMPANY_TCS` must match the selected Actor's real schema; the example JSON is only illustrative and is not guaranteed to work with an arbitrary Actor. Set the approval flag to `true` only after you have reviewed and approved that specific collection method. Supported placeholders are `{start_url}`, `{keyword}`, `{location}`, and `{max_results}`.

Test a single source first:

```powershell
python scripts/run_company_career_apify.py --source TCS --keyword "Software Engineer" --location India --max-results 5
```

Run every company source that has an Actor ID, input JSON, and explicit approval:

```powershell
python scripts/run_company_careers_batch.py --keyword "Software Engineer" --location India --max-results 10
```

The runner maps common job fields, fills a missing company name from the selected employer, validates records with the existing normalizer, writes collection history, and stores through the existing repository with `source_type="company_career"`. URL-hash deduplication remains in place. A successful Actor run does not guarantee that all returned jobs are India-based; review a small test dataset and apply the Actor's documented India/location filters before increasing the result limit.

No Actor is pre-approved or enabled by this code. Career sites that require login, bypass access controls, or prohibit the intended collection/reuse must not be scraped.

## Official company-career collection (no Apify Actor required)

The 25-company catalog uses official career-page URLs from the V4Career scope workbook. The built-in structured collector is a conservative alternative to generic page-text scraping. It only stores records marked as `schema.org/JobPosting` in JSON-LD, checks that the listing identifies the configured employer when that field is supplied, requires an India-indicating location, validates the job URL against configured official hosts, and rejects ordinary career/program descriptions. It does not bypass logins, CAPTCHAs, access controls, or robots/terms restrictions. Some career sites render listings in JavaScript or use a separate ATS; those sources may return zero results until a verified official ATS hostname or approved Actor is configured.

Run one company first:

```powershell
python scripts/run_company_career_structured.py --source TCS --max-results 10 --max-pages 20
```

Run all 25 catalog companies:

```powershell
python scripts/run_company_careers_structured_batch.py --max-results 50 --max-pages 60
```

The collector reports checked pages and actual JobPosting records. A successful zero-result run means pages were accessible but no valid India-located JobPosting JSON-LD was found; it does not fabricate vacancies. If no configured page can be fetched, the runner records a failed collection run when the database is available.

### Optional official ATS hosts

The collector starts at the official career URLs in `collectors/company_career_catalog.py` and follows job-like links only on that host and its subdomains. If an official career page links to a separate ATS domain, first verify that domain from the company's official site, then add only that hostname to the matching `CAREER_ALLOWED_HOSTS_<KEY>` variable in your local `.env`. Do not add a domain merely because it appears in a scraper result.

### Optional Apify fallback

The existing `scripts/run_company_career_apify.py` remains available for sites that do not expose usable structured listings. It still requires a reviewed Actor ID, a valid Actor-specific input JSON, an explicit `APIFY_ACCESS_APPROVED_<KEY>=true`, and `APIFY_API_TOKEN`. No Actor IDs, tokens, or approval flags are preconfigured by this change.

A source being listed in the UI or having this collector available does not prove it currently returns vacancies. Test each source and review the dataset/output before relying on its counts.


## Expanded 25-portal catalog

The UI now lists the 25 job portals in the scope workbook, with Naukri, Indeed,
Foundit and TimesJobs ordered first. Listing a portal is not proof that scraping
is configured. The existing known Actor/input defaults cover only Naukri,
Indeed, Foundit, Internshala, TimesJobs and Wellfound; Glassdoor and the other
portals require a reviewed Actor/API/feed plus the exact input JSON schema.
Unknown Actor schemas are intentionally rejected instead of being sent generic,
possibly invalid input. Approval flags remain false by default.

Company career sources are also expanded to the 25 official career URLs in the
scope workbook. The generic structured collector attempts only official-host
pages and stores only validated India-located `JobPosting` JSON-LD. A source
may return zero jobs if it renders listings in JavaScript, uses an external ATS,
blocks automated requests, or exposes no public structured data. Verify any
external ATS host from the company's own career page before adding it to
`CAREER_ALLOWED_HOSTS_<KEY>`. No actor is auto-approved by this update.
