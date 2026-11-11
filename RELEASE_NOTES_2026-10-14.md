# V4Career update — 2026-10-14

## Changes

1. Job portal checkboxes start unchecked. The dashboard shows a prompt until the user explicitly selects at least one portal. Refreshing source metadata preserves the user's current selection.
2. Changing the role or location no longer clears experience pre-emptively. The selected experience is retained if it is still available for the new filter combination; it is cleared only when the backend returns no matching option.
3. Excel export now has two worksheets: `Job Listings` with a concise description preview and `Full Descriptions` with readable, normalized text, wrapping, wider columns, row sizing, frozen headers, filters, alternating row shading, and clickable job URLs. Imported text is guarded against Excel formula interpretation.
4. Added candidate Apify Actor IDs and source-specific default input schemas for Indeed, Foundit, Internshala, TimesJobs, and Wellfound. The runner maps their common output fields into V4Career's existing job schema and continues to use the current MySQL repository/deduplication path.

## Important collection safety

- Candidate Actors are community-maintained and may change, stop working, or incur usage charges.
- All `APIFY_ACCESS_APPROVED_<PORTAL_KEY>` flags remain `false` by default. A source is skipped until explicitly approved locally.
- The Internshala Actor selected here supports keyword/mode and detail options but does not accept a location parameter; filter its collected records by location in V4Career.
- Do not commit or share `.env`. This ZIP intentionally excludes `.env`, `.git`, virtual environments, caches, and local data.

## Validation performed in this environment

- Python source compilation: passed.
- JavaScript syntax check (`node --check static/app.js`): passed.
- HTML parser check: passed.
- Source catalog unit tests: 3 passed.
- Live Flask/MySQL integration and actual Apify runs were not performed in this environment; configure a local token and database, then run a small approved test for each Actor before scheduling collection.

## Dashboard and salary-filter upgrade
- Added a dedicated Dashboard overview and made Job Portal open the existing listing workspace.
- Added database-backed cards and recent source/collection activity.
- Added normalized salary metadata, salary filters, salary display, and salary fields in Excel export.
- Added `scripts/migrations/20261014_add_salary_fields.sql`; apply once before starting this version.
- Added `README_PRODUCTION_UPGRADE.md`, `.env.example`, and `wsgi.py` for deployment preparation.
- Live `.env`, lock files, Python bytecode, and test caches are excluded from the delivery archive.
- Validation: Python compilation and JavaScript syntax checks passed; normalization/source-catalog tests passed (16 tests, 25 subtests). The Flask API suite could not be run in the build environment because Flask is not installed and package installation is unavailable.
