# Local implementation notes — 2026-10-20

## Changes in this review build
- Added `/api/dashboard/trend`, a database-backed 14-day job creation count series with zero-filled days.
- Added a compact 14-day trend chart to the Dashboard using existing HTML/CSS/JavaScript (no new chart dependency).
- Added a Dashboard-to-Reports navigation action beside Recent Collection Activity.
- Preserved existing job listing markup and collection workflow.

## Important scope status
This is an incremental review build, **not a completion of the full requested upgrade**. The six separate Reports datasets and their dedicated filters/exports, expanded Data Quality checks, and verified/ready-to-run employer-specific collectors still require implementation and testing. The existing Reports page remains the current overview.

## Local setup (Windows PowerShell)
```powershell
cd .\V4Career_UI_Upgrade
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env with your own local database settings and admin credentials.
python app.py
```
If `.env.example` is not present, create `.env` from the variable names documented in `README.md`; never copy credentials from another environment into a shared ZIP.

## Checks performed in this environment
- Python compilation: passed for `app.py`, `collectors/*.py`, and `collectors/sources/*.py`.
- JavaScript syntax (`node --check static/app.js`): passed.
- Pytest: blocked because Flask is not installed in this execution environment. With `PYTHONPATH=.` set, test collection reached the missing-Flask dependency. No database-backed tests are claimed as passed.
- No production database was contacted and no deployment or GitHub push was performed.
