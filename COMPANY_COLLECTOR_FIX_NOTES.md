# V4Career company collector update — 2026-10-21

## Changes in this update
- Added a dedicated Deloitte India SuccessFactors listing collector. It recognizes official vacancy links of the form `/job/<slug>/<numeric-id>/`, paginates using `startrow`, normalizes the jobs and passes them into the existing save pipeline.
- Kept the working Infosys public search API collector unchanged.
- Kept the Amazon official JSON search collector unchanged.
- Preserved all five configured companies in `collectors/company_career_catalog.py`, which is the source used by the UI/company API.
- Added a mocked test for Deloitte SuccessFactors job-card extraction.

## Verification
Targeted tests:
`python -m pytest -q tests/test_company_career_structured.py tests/test_company_career_catalog.py tests/test_source_catalog.py tests/test_normalization.py tests/test_db_compatibility.py`

Result: 33 passed, 12 subtests passed.

The full test suite could not be collected in this packaging environment because Flask is not installed (`ModuleNotFoundError: flask`).

## Important live status
- Infosys: user's latest run found 100 and updated 100.
- Amazon: user's latest run found 100 and inserted 100.
- Wipro: still requires a live test of its client-side SAP SuccessFactors widget/API. The current feed and server-rendered HTML did not expose vacancy cards.
- Accenture: still requires a live test of the current client-side search data endpoint. The fetched HTML pages did not expose vacancy cards.
- Deloitte: collector is implemented and has mocked parser coverage, but has not been live-run from this packaging environment.

Do not describe Wipro, Accenture, or Deloitte as live-verified until the user's collector output confirms `jobs_found > 0` and records are inserted or updated. No production database or Render deployment was changed.
