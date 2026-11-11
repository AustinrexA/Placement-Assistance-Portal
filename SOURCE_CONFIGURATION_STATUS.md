# V4Career source catalog and configuration status

Updated from `V4Career_Scope_Job_Portals_and_Companies.xlsx`.

## Job portals

All 25 portals in the scope sheet are listed in the catalog and exposed by the Job Portal API/UI. Naukri, Indeed, Foundit, and TimesJobs are ordered first. The sidebar includes separate controls for selecting the four popular portals or all portals.

Existing candidate Actor IDs and input defaults are available for:
- Naukri
- Indeed
- Foundit
- Internshala
- TimesJobs
- Wellfound

These are community Actor candidates, not guarantees of current availability or permission. Collection remains disabled unless the matching `APIFY_ACCESS_APPROVED_<KEY>` is explicitly set to `true`. For new portals, configure a reviewed Actor ID and `APIFY_INPUT_<KEY>` using the Actor's actual Input schema. Unknown portals no longer receive a guessed generic input. The Glassdoor Actor shown in the user's screenshot (`bebity~glassdoor-jobs-scraper`) is documented as a candidate only; its input schema still needs review before use.

## Company career sites

All 25 companies from the scope sheet are present in the company catalog and visible in the Companies sidebar. The official-site collector is available for all entries, but it only stores validated `schema.org/JobPosting` records whose location indicates India and whose URLs remain on configured official hosts.

Specialized collector paths already exist for Infosys, Wipro, Amazon, Accenture, and Deloitte. The catalog's verification flag is not set for the remaining companies until live results have been validated. Some sites may return zero jobs because listings are JavaScript-rendered, use an external ATS, block requests, or do not publish JobPosting JSON-LD. A zero-result run is not a fabricated vacancy count.

## Safety and secrets

- All Actor approval flags in `.env.example` default to `false`.
- Do not enable collection until you review the Actor's current input schema, price, terms, and authorization.
- `.env` and `.git` are intentionally excluded from this ZIP so credentials and repository history are not redistributed.
- Copy the needed variable names into your local `.env`; do not replace existing DB settings.
