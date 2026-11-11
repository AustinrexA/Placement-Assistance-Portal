# V4Career: 11 active UI portals + 3 portal retests

## UI allowlist (shown only when the existing approval/token/Actor checks pass)
Naukri, Indeed, Foundit, TimesJobs, Internshala, Wellfound, Glassdoor, Hirist, Shine.com, iimjobs, Jooble.

Freshersworld, National Career Service (NCS), and QuikrJobs remain available to the CLI for retesting but are deliberately excluded from the UI allowlist until they save jobs successfully. Other non-verified portals are also excluded from the Job Portal UI. Existing database rows and job records are not deleted.

## Input fixes
- Freshersworld: removed unsupported `collectDetails` input.
- NCS: removed unsupported `retries` input.
- QuikrJobs: maps an `India` location request to `Bengaluru`, because the Actor rejected `India` as a city. This is a city-scoped test, not nationwide coverage.

Important: `APIFY_INPUT_FRESHERSWORLD`, `APIFY_INPUT_NATIONAL_CAREER_SERVICE_NCS`, or `APIFY_INPUT_QUIKRJOBS` in `.env` overrides these defaults. Remove or correct those variables for the defaults above to apply. `.env` and API tokens are not included in this package.

## Small live test commands
Run from the project root, after confirming `.env` has APIFY_API_TOKEN and APIFY_ACCESS_APPROVED_<KEY>=true for each source. Start with `--max-results 3`.

```powershell
python scripts/run_source_apify.py --source Naukri --keyword "Software Engineer" --location India --max-results 3
python scripts/run_source_apify.py --source Indeed --keyword "Software Engineer" --location India --max-results 3
python scripts/run_source_apify.py --source Foundit --keyword "Software Engineer" --location India --max-results 3
python scripts/run_source_apify.py --source TimesJobs --keyword "Software Engineer" --location India --max-results 3
python scripts/run_source_apify.py --source Internshala --keyword "Software Engineer" --location India --max-results 3
python scripts/run_source_apify.py --source Wellfound --keyword "Software Engineer" --location India --max-results 3
python scripts/run_source_apify.py --source Glassdoor --keyword "Software Engineer" --location India --max-results 3
python scripts/run_source_apify.py --source Hirist --keyword "Software Engineer" --location India --max-results 3
python scripts/run_source_apify.py --source Shine.com --keyword "Software Engineer" --location India --max-results 3
python scripts/run_source_apify.py --source iimjobs --keyword "Software Engineer" --location India --max-results 3
python scripts/run_source_apify.py --source Jooble --keyword "Software Engineer" --location India --max-results 3
python scripts/run_source_apify.py --source Freshersworld --keyword "Software Engineer" --location India --max-results 3
python scripts/run_source_apify.py --source "National Career Service (NCS)" --keyword "Software Engineer" --location India --max-results 3
python scripts/run_source_apify.py --source QuikrJobs --keyword "Software Engineer" --location India --max-results 3
```

Do not test LinkedIn Jobs with the current input: a prior run saved hundreds of jobs despite a small requested limit.
