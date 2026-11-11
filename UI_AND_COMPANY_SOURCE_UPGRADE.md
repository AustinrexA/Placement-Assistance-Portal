# V4Career — Company source filtering and report UI upgrade

## Included changes

- Company career sources remain distinct from general job portals in the sidebar and database.
- Selecting one or more company checkboxes now filters the same Job Listings dataset by the selected company-career source IDs. Selecting a company does not itself start a scrape; collectors remain independently run/configured.
- Portal and company source IDs are combined for the existing job list, dependent facets and normal job export. Clearing filters preserves selected sources.
- Company entries display `Unverified` until an approved Actor configuration exists. The built-in structured collector's presence is not treated as proof that a company site is currently collectible.
- The Reports page is simplified to four database-backed summary metrics, essential keyword/source/company/location/date filters, sorting, pagination, Excel/CSV export, and recent collection activity with error details.
- The report API now supports safe sort choices, company-career source-type filtering, and the report export supports an inclusive posted-to date and CSV format.
- Sidebar select-all checkboxes are positioned before the Job Portal and Companies labels.
- Styling uses a restrained navy/slate/teal gradient, compact report cards, clearer hierarchy and responsive report filters.

## Important collection limitation

The company catalog and structured collector are present for TCS, Infosys, Wipro, HCLTech, Accenture, Cognizant, Capgemini, Amazon, Microsoft, Google, IBM, Adobe, Zoho, Freshworks and Paytm. This does **not** mean all 15 sites are live operational sources. Each source still requires successful access to genuine individual job listings. TCS returned HTTP 403 on all four configured official pages in the last reported run, so TCS collection remains blocked until a verified official feed/ATS endpoint or reviewed permitted collector is available.

## Verification performed for this upgrade

- `python -m py_compile app.py tests/test_api.py collectors/company_career_structured.py scripts/run_company_career_structured.py` — passed.
- `node --check static/app.js` — passed.
- HTML parse and duplicate-ID check — passed; no duplicate IDs found.
- Full pytest suite could not be run in this build environment because Flask is not installed and package installation is unavailable. Run `python -m pytest -q` in the project's Windows virtual environment before deployment.

No database migration, production database write, credential change, or deployment was performed as part of this UI and source-filter change.

## Superseding UI refinement (2026-10-21)

- The sidebar now shows only Foundit, Glassdoor, Indeed, Internshala, Naukri, TimesJobs and Wellfound. Legacy source rows and their jobs are not deleted; non-listed sources are simply hidden from the portal UI/API response.
- Removed the Companies checkbox group from the sidebar so company career sources can be added one at a time after their collector is validated. The catalog is staged to Infosys, Amazon and Wipro only.
- Replaced the Job Portal dropdown chevron with a plus/minus glyph, aligned the icon/master-checkbox/label columns, increased sidebar spacing, softened the orange accent, and increased UI font sizes.
- Corrected Infosys API normalization to read the live API's `postingTitle`, `createdOn`, description fields and min/max experience fields. This mapping is covered by the collector tests; a database write and UI persistence run still need to be verified in the user's local environment.
- Verification in this build container: 32 tests passed and 13 subtests passed across catalog, structured collector, normalization and database-compatibility modules. Full API tests could not be collected because Flask is not installed in this environment.
